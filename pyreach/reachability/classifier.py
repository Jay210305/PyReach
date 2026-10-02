"""Reachability classifier — pure decision logic (S3-T6).

Centralizes the reachability decision so the analyzer stays purely mechanical
and the heuristics are unit-testable in isolation. This is the primary control
for the R2 "zero critical false negatives" policy: uncertainty always resolves
upward to ``POTENTIALLY_REACHABLE``.

This module has no NetworkX dependency — it consumes :class:`TraversalOutcome`
(evidence) and :class:`SymbolContext` (static facts) and emits the final
:class:`ReachabilityResult`.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyreach.parsers.osv_json import Vulnerability
from pyreach.reachability.contracts import (
    MAX_PATHS,
    ReachabilityResult,
    ReachabilityStatus,
    TraversalOutcome,
)

REASON_REACHABLE = "Static call path found from {entry} (depth {depth})."
REASON_DYNAMIC = "Dynamic call pattern (eval/exec/getattr/importlib) on path."
REASON_IMPORTED_UNRESOLVED = "Vulnerable package imported but exact symbol unresolved."
REASON_PACKAGE_NOT_IMPORTED = "No call path found and package not imported."
REASON_DEPTH = "Call graph depth limit k reached before resolution."
REASON_NO_PATH = "No call path found."
REASON_UNRESOLVED_IMPORTS = "Import resolution incomplete; cannot rule out reachability."


@dataclass
class SymbolContext:
    """Static facts about a vulnerable symbol, decoupled from the graph."""

    symbol_fqn: str
    vulnerability: Vulnerability
    package_imported: bool
    exact_node_exists: bool
    dynamic_in_chain: bool
    unresolved_imports: bool
    max_depth_exceeded: bool


class ReachabilityClassifier:
    """Map traversal evidence + symbol context to a conservative verdict.

    The ordered rules encode the decision matrix from
    ``06-ast-and-callgraph-engine.md`` §4.2:

    1. A proven static path -> ``REACHABLE``.
    2. Any dynamic/unresolved signal on the path -> ``POTENTIALLY_REACHABLE``.
    3. Package not imported -> ``NOT_REACHABLE`` (unless imports unresolved).
    4. Package imported but exact symbol node absent -> ``POTENTIALLY_REACHABLE``.
    5. Exact node exists but imports unresolved -> ``POTENTIALLY_REACHABLE``.
    6. Depth limit reached with no dynamic -> ``NOT_REACHABLE``.
    7. Otherwise (no path, clean) -> ``NOT_REACHABLE``.

    ``NOT_REACHABLE`` is only emitted when the analysis is fully certain, so a
    false negative is impossible unless a rule above is mis-ordered.
    """

    def classify(self, evidence: TraversalOutcome, context: SymbolContext) -> ReachabilityResult:
        if evidence.status == "REACHABLE" and evidence.paths:
            return self._reachable(evidence, context)

        if context.dynamic_in_chain or evidence.encountered_dynamic:
            return self._result(context, "POTENTIALLY_REACHABLE", REASON_DYNAMIC)

        if not context.package_imported:
            if context.unresolved_imports:
                return self._result(context, "POTENTIALLY_REACHABLE", REASON_UNRESOLVED_IMPORTS)
            return self._result(context, "NOT_REACHABLE", REASON_PACKAGE_NOT_IMPORTED)

        if not context.exact_node_exists:
            return self._result(context, "POTENTIALLY_REACHABLE", REASON_IMPORTED_UNRESOLVED)

        if context.unresolved_imports:
            return self._result(context, "POTENTIALLY_REACHABLE", REASON_UNRESOLVED_IMPORTS)

        if context.max_depth_exceeded or evidence.depth_exceeded:
            return self._result(context, "NOT_REACHABLE", REASON_DEPTH)

        return self._result(context, "NOT_REACHABLE", REASON_NO_PATH)

    def _reachable(self, evidence: TraversalOutcome, context: SymbolContext) -> ReachabilityResult:
        all_paths = sorted(evidence.paths)
        entry_points = sorted({path[0] for path in all_paths})
        entry = entry_points[0]
        depth = min(len(path) - 1 for path in all_paths)
        return ReachabilityResult(
            vulnerability=context.vulnerability,
            status="REACHABLE",
            entry_points_reached=entry_points,
            paths=all_paths[:MAX_PATHS],
            reasoning=REASON_REACHABLE.format(entry=entry, depth=depth),
        )

    def _result(
        self, context: SymbolContext, status: ReachabilityStatus, reasoning: str
    ) -> ReachabilityResult:
        return ReachabilityResult(
            vulnerability=context.vulnerability,
            status=status,
            entry_points_reached=[],
            paths=[],
            reasoning=reasoning,
        )
