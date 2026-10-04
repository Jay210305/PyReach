"""CGEdge — immutable directed edge per spec §3.3 and S3-T1 Decision B."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from pyreach.callgraph.nodes import CGNode
from pyreach.exceptions import AnalysisError

EdgeType = Literal["STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"]

_VALID_EDGE_TYPES: set[str] = {"STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"}

# Precedence for deduplicating parallel edges: on equal confidence the stronger
# type wins (spec §4.5). IMPORT sits below STATIC/INHERITANCE but above DYNAMIC.
_EDGE_TYPE_PRECEDENCE = {"STATIC": 4, "INHERITANCE": 3, "IMPORT": 2, "DYNAMIC": 1}


def add_edge(
    graph: nx.DiGraph, caller: str, callee: str, edge_type: EdgeType, confidence: float
) -> None:
    """Add a directed edge keeping the winner on duplicates.

    ``DiGraph`` collapses parallel edges with last-write-wins, so this guard is
    what keeps edge insertion order-independent and deterministic: a new edge is
    kept only when it beats the existing one on ``(confidence, type precedence)``.
    """
    existing = graph.get_edge_data(caller, callee)
    if existing is not None:
        old_key = (
            float(existing.get("confidence", 0.0)),
            _EDGE_TYPE_PRECEDENCE.get(str(existing.get("edge_type", "DYNAMIC")), 0),
        )
        if (confidence, _EDGE_TYPE_PRECEDENCE.get(edge_type, 0)) <= old_key:
            return
    graph.add_edge(caller, callee, edge_type=edge_type, confidence=confidence)


@dataclass(frozen=True)
class CGEdge:
    caller: CGNode
    callee: CGNode
    edge_type: EdgeType
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.edge_type not in _VALID_EDGE_TYPES:
            raise AnalysisError(f"Invalid edge_type: {self.edge_type!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise AnalysisError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")

    @property
    def is_dynamic(self) -> bool:
        return self.edge_type == "DYNAMIC"

    def to_row(self, node_ids: Mapping[str, int]) -> dict[str, object]:
        """Serialize to ``cg_edges`` columns, resolving FQNs to node ids."""
        return {
            "caller_id": node_ids[self.caller.fqn],
            "callee_id": node_ids[self.callee.fqn],
            "edge_type": self.edge_type,
            "confidence": self.confidence,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, object], nodes_by_id: Mapping[int, CGNode]) -> CGEdge:
        """Reconstruct an edge from a ``cg_edges`` row and an id -> node map."""
        return cls(
            caller=nodes_by_id[int(row["caller_id"])],  # type: ignore[call-overload]
            callee=nodes_by_id[int(row["callee_id"])],  # type: ignore[call-overload]
            edge_type=row["edge_type"],  # type: ignore[arg-type]
            confidence=float(row["confidence"]),  # type: ignore[arg-type]
        )


def add_cgedge(graph: nx.DiGraph, edge: CGEdge) -> None:
    add_edge(graph, edge.caller.fqn, edge.callee.fqn, edge.edge_type, edge.confidence)
