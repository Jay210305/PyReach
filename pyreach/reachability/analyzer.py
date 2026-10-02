"""Bounded reachability analysis over the call graph (S3-T5).

Determines, for each vulnerable symbol, whether any application entry point
can reach it within ``max_depth`` hops. The traversal is iterative BFS
(never recursion), cycle-safe via a visited set, and bounded by depth to keep
runtime within the R1 budget.

Final classification is delegated to
:class:`~pyreach.reachability.classifier.ReachabilityClassifier` (S3-T6), which
encodes the conservative decision matrix — uncertainty always resolves upward
to ``POTENTIALLY_REACHABLE`` (R2, zero critical false negatives).

The memoization caches are in-memory and per-run; call :func:`clear_cache`
between runs/tests. A cross-run cache (SQLite ``reachability_results``) is a
Sprint 4 concern.
"""

from __future__ import annotations

import logging
from collections import deque

import networkx as nx

# mypy: disable-error-code="import-untyped"
from pyreach.callgraph.engine import SENTINEL_DYNAMIC, SENTINEL_UNRESOLVED
from pyreach.parsers.osv_json import Vulnerability
from pyreach.reachability.classifier import ReachabilityClassifier, SymbolContext
from pyreach.reachability.contracts import (
    ReachabilityResult,
    ReachabilityStatus,
    TraversalOutcome,
)

logger = logging.getLogger(__name__)

_traversal_cache: dict[tuple[str, str, int], TraversalOutcome] = {}
_package_cache: dict[str, bool] = {}


def clear_cache() -> None:
    """Reset the in-memory traversal and package-import caches."""
    _traversal_cache.clear()
    _package_cache.clear()


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


def _package_imported(graph: nx.DiGraph, package: str) -> bool:
    cached = _package_cache.get(package)
    if cached is not None:
        return cached
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
) -> dict[str, ReachabilityResult]:
    """Classify reachability for every affected symbol of every vulnerability.

    Results are keyed by symbol FQN (one entry per affected symbol).
    """
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    classifier = ReachabilityClassifier()
    results: dict[str, ReachabilityResult] = {}
    for vuln in vulnerabilities:
        for symbol in vuln.affected_symbols:
            results[symbol] = _analyze_symbol(
                graph, entry_points, vuln, symbol, max_depth, classifier
            )
    return results


def _analyze_symbol(
    graph: nx.DiGraph,
    entry_points: list[str],
    vuln: Vulnerability,
    symbol: str,
    max_depth: int,
    classifier: ReachabilityClassifier,
) -> ReachabilityResult:
    exact_node_exists = symbol in graph
    if exact_node_exists:
        evidence = _aggregate_evidence(graph, entry_points, symbol, max_depth)
    else:
        evidence = TraversalOutcome("NOT_REACHABLE", [], False, False)

    context = SymbolContext(
        symbol_fqn=symbol,
        vulnerability=vuln,
        package_imported=_package_imported(graph, vuln.package_name),
        exact_node_exists=exact_node_exists,
        dynamic_in_chain=evidence.encountered_dynamic,
        unresolved_imports=_unresolved_imports(graph),
        max_depth_exceeded=evidence.depth_exceeded,
    )
    return classifier.classify(evidence, context)
