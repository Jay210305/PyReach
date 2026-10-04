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

import networkx as nx

from pyreach.ast.builder import ModuleAST
from pyreach.callgraph.engine import SENTINEL_DYNAMIC, SENTINEL_UNRESOLVED
from pyreach.exceptions import ConfigError
from pyreach.osv.mapper import Vulnerability
from pyreach.reachability.classifier import ReachabilityClassifier, SymbolContext
from pyreach.reachability.contracts import (
    ReachabilityResult,
    ReachabilityStatus,
    TraversalOutcome,
)

logger = logging.getLogger(__name__)

MAX_DEPTH = 7

_traversal_cache: dict[tuple[str, str, int], TraversalOutcome] = {}
_package_cache: dict[str, bool] = {}


def clear_cache() -> None:
    """Reset the in-memory traversal and package-import caches."""
    _traversal_cache.clear()
    _package_cache.clear()


def _dynamic_import_targets(module: ModuleAST) -> set[str]:
    """Top-level package names imported dynamically (``importlib.import_module``)."""
    targets: set[str] = set()
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_dynamic_import = (isinstance(func, ast.Name) and func.id == "__import__") or (
            isinstance(func, ast.Attribute) and func.attr == "import_module"
        )
        if not is_dynamic_import or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            top = arg.value.split(".")[0]
            if top:
                targets.add(top)
    return targets


def imported_packages(modules: Iterable[ModuleAST]) -> set[str]:
    """Return the set of top-level package names imported by *modules*.

    This is the "application import set" consumed by ``package_imported``
    detection (S3-T6 Pitfalls): library nodes in the graph must not count as
    "imported by the application". Static imports (``import``/``from ...
    import``) and dynamic imports (``importlib.import_module``/``__import__``)
    both count, since a dynamically imported package is still reachable.
    """
    packages: set[str] = set()
    for mod in modules:
        for fqn in mod.imports.values():
            top = fqn.split(".")[0]
            if top:
                packages.add(top)
        packages.update(_dynamic_import_targets(mod))
    return packages


def _traverse(graph: nx.DiGraph, entry: str, target: str, max_depth: int) -> TraversalOutcome:
    key = (entry, target, max_depth)
    cached = _traversal_cache.get(key)
    if cached is not None:
        return cached
    outcome = _traverse_uncached(graph, entry, target, max_depth)
    _traversal_cache[key] = outcome
    return outcome


def _traverse_uncached(
    graph: nx.DiGraph, entry: str, target: str, max_depth: int
) -> TraversalOutcome:
    """Iterative depth-limited BFS from ``entry`` toward ``target``.

    Returns the shortest path when found, plus whether a dynamic/unresolved
    edge was crossed anywhere in the reachable frontier and whether the depth
    bound cut the search short.
    """
    if entry not in graph:
        return TraversalOutcome("NOT_REACHABLE", [], False, False)
    if entry == target:
        return TraversalOutcome("REACHABLE", [[entry]], False, False)

    queue: deque[tuple[str, list[str], int]] = deque([(entry, [entry], 0)])
    visited: set[str] = {entry}
    encountered_dynamic = False
    depth_exceeded = False

    while queue:
        node, path, depth = queue.popleft()
        if depth > max_depth:
            depth_exceeded = True
            continue
        for successor in sorted(graph.successors(node)):
            edge = graph.get_edge_data(node, successor) or {}
            if edge.get("edge_type") == "DYNAMIC" or successor in (
                SENTINEL_DYNAMIC,
                SENTINEL_UNRESOLVED,
            ):
                encountered_dynamic = True
            if successor == target:
                if depth + 1 <= max_depth:
                    return TraversalOutcome(
                        "REACHABLE", [path + [successor]], encountered_dynamic, depth_exceeded
                    )
                depth_exceeded = True
                continue
            if successor in visited:
                continue
            visited.add(successor)
            if depth + 1 > max_depth:
                depth_exceeded = True
            queue.append((successor, path + [successor], depth + 1))

    status: ReachabilityStatus = "POTENTIALLY_REACHABLE" if encountered_dynamic else "NOT_REACHABLE"
    return TraversalOutcome(status, [], encountered_dynamic, depth_exceeded)


def _package_imported(
    graph: nx.DiGraph, package: str, application_imports: set[str] | None
) -> bool:
    cached = _package_cache.get(package)
    if cached is not None:
        return cached
    if application_imports is not None:
        imported = package in application_imports
    else:
        prefix = f"{package}."
        imported = package in graph or any(n.startswith(prefix) for n in graph)
    _package_cache[package] = imported
    return imported


def _unresolved_imports(graph: nx.DiGraph) -> bool:
    """Conservative proxy: unresolved names exist anywhere in the graph.

    The ``<UNRESOLVED>`` sentinel records call sites whose target could not be
    resolved. Their presence means we cannot rule out an unresolved import, so
    the classifier must not emit ``NOT_REACHABLE`` for packages that merely
    appear unimported.
    """
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
) -> dict[tuple[str, str], ReachabilityResult]:
    """Classify reachability for every affected symbol of every vulnerability.

    Results are keyed by ``(osv_id, symbol)`` so two advisories that share an
    affected symbol never overwrite each other.
    """
    if max_depth < 0 or max_depth > MAX_DEPTH:
        raise ConfigError(f"max_depth must be in [0, {MAX_DEPTH}], got {max_depth}")

    clear_cache()

    classifier = ReachabilityClassifier()
    results: dict[tuple[str, str], ReachabilityResult] = {}
    for vuln in vulnerabilities:
        for symbol in vuln.affected_symbols:
            results[(vuln.osv_id, symbol)] = _analyze_symbol(
                graph, entry_points, vuln, symbol, max_depth, classifier, application_imports
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
) -> ReachabilityResult:
    exact_node_exists = symbol in graph
    if exact_node_exists:
        evidence = _aggregate_evidence(graph, entry_points, symbol, max_depth)
    else:
        evidence = TraversalOutcome("NOT_REACHABLE", [], False, False)

    context = SymbolContext(
        symbol_fqn=symbol,
        vulnerability=vuln,
        package_imported=_package_imported(graph, vuln.package_name, application_imports),
        exact_node_exists=exact_node_exists,
        dynamic_in_chain=evidence.encountered_dynamic,
        unresolved_imports=_unresolved_imports(graph),
        max_depth_exceeded=evidence.depth_exceeded,
    )
    return classifier.classify(evidence, context)
