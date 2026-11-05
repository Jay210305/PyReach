"""Bounded reachability analysis over the call graph (S3-T5).

Determines, for each vulnerable symbol, whether any application entry point
can reach it within ``max_depth`` hops. The traversal is iterative BFS
(never recursion), cycle-safe via a visited set, and bounded by depth to keep
runtime within the R1 budget.

Final classification is delegated to
:class:`~pyreach.reachability.classifier.ReachabilityClassifier` (S3-T6), which
encodes the conservative decision matrix — uncertainty always resolves upward
to ``POTENTIALLY_REACHABLE`` (R2, zero critical false negatives).

The memoization caches are per-run: :func:`analyze_reachability` clears them at
the start of every call, so a changed graph or import set cannot leak stale
verdicts into the next run.
"""

from __future__ import annotations

import ast
import logging
from collections import deque
from collections.abc import Iterable
from typing import Any

import networkx as nx

from pyreach.ast.builder import ModuleAST
from pyreach.callgraph.engine import SENTINEL_DYNAMIC, SENTINEL_UNRESOLVED
from pyreach.exceptions import ConfigError
from pyreach.osv.mapper import Vulnerability
from pyreach.parsers.manifest import normalize_name
from pyreach.reachability.classifier import ReachabilityClassifier, SymbolContext
from pyreach.reachability.contracts import (
    ReachabilityResult,
    ReachabilityStatus,
    TraversalOutcome,
)

logger = logging.getLogger(__name__)

MAX_DEPTH = 7

_traversal_cache: dict[tuple[str, str, int], TraversalOutcome] = {}
_package_cache: dict[tuple[str, str], bool] = {}


class ReachabilityResults(dict[Any, ReachabilityResult]):
    """Result mapping supporting both (osv_id, package_name, symbol) and (osv_id, symbol) keys."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._by_two: dict[tuple[str, str], ReachabilityResult] = {}

    def __setitem__(self, key: Any, value: ReachabilityResult) -> None:
        super().__setitem__(key, value)
        if isinstance(key, tuple):
            if len(key) == 3:
                self._by_two[(key[0], key[2])] = value
            elif len(key) == 2:
                self._by_two[(key[0], key[1])] = value

    def __getitem__(self, key: Any) -> ReachabilityResult:
        if isinstance(key, tuple) and len(key) == 2 and key in self._by_two:
            return self._by_two[key]
        return super().__getitem__(key)

    def __contains__(self, key: Any) -> bool:
        if isinstance(key, tuple) and len(key) == 2 and key in self._by_two:
            return True
        return super().__contains__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        if isinstance(key, tuple) and len(key) == 2 and key in self._by_two:
            return self._by_two[key]
        return super().get(key, default)


def clear_cache() -> None:
    """Reset the in-memory traversal and package-import caches."""
    _traversal_cache.clear()
    _package_cache.clear()


def imported_packages(modules: Iterable[ModuleAST]) -> set[str]:
    """Collect top-level package names imported by any module in *modules*."""
    packages: set[str] = set()
    for mod in modules:
        for node in ast.walk(mod.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    packages.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    packages.add(node.module.split(".")[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "__import__"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                packages.add(node.args[0].value.split(".")[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                packages.add(node.args[0].value.split(".")[0])
    return packages


def _traverse(
    graph: nx.DiGraph, entry_point: str, symbol: str, max_depth: int
) -> TraversalOutcome:
    """Bounded BFS memoized by ``(entry_point, symbol, max_depth)``."""
    key = (entry_point, symbol, max_depth)
    cached = _traversal_cache.get(key)
    if cached is not None:
        return cached

    outcome = _traverse_uncached(graph, entry_point, symbol, max_depth)
    _traversal_cache[key] = outcome
    return outcome


def _traverse_uncached(
    graph: nx.DiGraph, entry_point: str, symbol: str, max_depth: int
) -> TraversalOutcome:
    if entry_point not in graph:
        return TraversalOutcome("NOT_REACHABLE", [], False, False)

    queue: deque[tuple[str, list[str], int]] = deque([(entry_point, [entry_point], 0)])
    visited: set[str] = {entry_point}
    found_paths: list[list[str]] = []
    encountered_dynamic = False
    depth_exceeded = False

    while queue:
        current, path, depth = queue.popleft()

        if current == symbol:
            found_paths.append(path)
            continue

        if depth >= max_depth:
            if graph.out_degree(current) > 0:
                depth_exceeded = True
            continue

        for _, successor, edge_data in graph.out_edges(current, data=True):
            if successor == SENTINEL_DYNAMIC or edge_data.get("edge_type") == "DYNAMIC":
                encountered_dynamic = True
                continue

            if successor == SENTINEL_UNRESOLVED:
                continue

            if successor == symbol:
                found_paths.append(path + [successor])
                continue

            if successor not in visited:
                visited.add(successor)
                queue.append((successor, path + [successor], depth + 1))

    status: ReachabilityStatus
    if found_paths:
        status = "REACHABLE"
    elif encountered_dynamic:
        status = "POTENTIALLY_REACHABLE"
    else:
        status = "NOT_REACHABLE"

    return TraversalOutcome(status, found_paths, encountered_dynamic, depth_exceeded)


def _package_imported(
    graph: nx.DiGraph,
    package: str,
    symbol: str,
    application_imports: set[str] | None,
    package_import_names: dict[str, set[str]] | None,
) -> bool:
    norm_package = normalize_name(package)
    symbol_top = symbol.split(".", 1)[0]
    candidates = {norm_package}
    if symbol_top != "*":
        candidates.add(normalize_name(symbol_top))
    if package_import_names is not None:
        candidates.update(
            normalize_name(name) for name in package_import_names.get(norm_package, set())
        )
    key = (norm_package, symbol_top)
    cached = _package_cache.get(key)
    if cached is not None:
        return cached
    if application_imports is not None:
        imported = any(normalize_name(name) in candidates for name in application_imports)
    else:
        imported = any(normalize_name(node.split(".")[0]) in candidates for node in graph)
    _package_cache[key] = imported
    return imported


def _unresolved_imports(graph: nx.DiGraph) -> bool:
    return SENTINEL_UNRESOLVED in graph and graph.in_degree(SENTINEL_UNRESOLVED) > 0


def _aggregate_evidence(
    graph: nx.DiGraph, entry_points: list[str], symbol: str, max_depth: int
) -> TraversalOutcome:
    """Merge per-entry traversal outcomes into one symbol-level outcome."""
    paths: list[list[str]] = []
    any_dynamic = False
    any_depth_exceeded = False
    for entry in entry_points:
        outcome = _traverse(graph, entry, symbol, max_depth)
        if outcome.status == "REACHABLE":
            paths.extend(outcome.paths)
        any_dynamic = any_dynamic or outcome.encountered_dynamic
        any_depth_exceeded = any_depth_exceeded or outcome.depth_exceeded

    status: ReachabilityStatus = (
        "REACHABLE" if paths else ("POTENTIALLY_REACHABLE" if any_dynamic else "NOT_REACHABLE")
    )
    return TraversalOutcome(status, paths, any_dynamic, any_depth_exceeded)


def analyze_reachability(
    graph: nx.DiGraph,
    entry_points: list[str],
    vulnerabilities: list[Vulnerability],
    max_depth: int = 5,
    application_imports: set[str] | None = None,
    package_import_names: dict[str, set[str]] | None = None,
) -> ReachabilityResults:
    """Classify reachability for every affected symbol of every vulnerability.

    Results are keyed by ``(osv_id, package_name, symbol)`` and also indexable
    by ``(osv_id, symbol)``.
    """
    if max_depth < 0 or max_depth > MAX_DEPTH:
        raise ConfigError(f"max_depth must be in [0, {MAX_DEPTH}], got {max_depth}")

    clear_cache()

    classifier = ReachabilityClassifier()
    results = ReachabilityResults()
    for vuln in vulnerabilities:
        for symbol in vuln.affected_symbols:
            results[(vuln.osv_id, vuln.package_name, symbol)] = _analyze_symbol(
                graph,
                entry_points,
                vuln,
                symbol,
                max_depth,
                classifier,
                application_imports,
                package_import_names,
            )
    return results


def _analyze_symbol(
    graph: nx.DiGraph,
    entry_points: list[str],
    vuln: Vulnerability,
    symbol: str,
    max_depth: int,
    classifier: ReachabilityClassifier,
    application_imports: set[str] | None,
    package_import_names: dict[str, set[str]] | None,
) -> ReachabilityResult:
    exact_node_exists = symbol in graph
    if exact_node_exists:
        evidence = _aggregate_evidence(graph, entry_points, symbol, max_depth)
    else:
        evidence = TraversalOutcome("NOT_REACHABLE", [], False, False)

    context = SymbolContext(
        symbol_fqn=symbol,
        vulnerability=vuln,
        package_imported=_package_imported(
            graph, vuln.package_name, symbol, application_imports, package_import_names
        ),
        exact_node_exists=exact_node_exists,
        dynamic_in_chain=evidence.encountered_dynamic,
        unresolved_imports=_unresolved_imports(graph),
        max_depth_exceeded=evidence.depth_exceeded,
    )
    return classifier.classify(evidence, context)
