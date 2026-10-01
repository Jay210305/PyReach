"""CGEdge — immutable directed edge per spec §3.3 and S3-T1 Decision B."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pyreach.callgraph.nodes import CGNode
from pyreach.exceptions import AnalysisError

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]

EdgeType = Literal["STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"]

_VALID_EDGE_TYPES: set[str] = {"STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"}


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
        # dataclass is frozen, so use object.__setattr__ if coercion needed — not needed here.

    @property
    def is_dynamic(self) -> bool:
        return self.edge_type == "DYNAMIC"


def add_cgedge(graph: object, edge: CGEdge) -> None:
    if nx is None:  # pragma: no cover
        raise AnalysisError("networkx not installed")
    assert isinstance(graph, nx.DiGraph)
    # dedup by (caller.fqn, callee.fqn, edge_type) — matches schema UNIQUE(caller_id, callee_id, edge_type)
    # DiGraph collapses (caller,callee) to one edge; we keep edge_type in attrs to distinguish
    # S3-T2 council note: if edge_type differs, both can co-exist logically but DiGraph keeps last;
    # S3-T3 will document first-wins or max-confidence policy. Here we store edge_type explicitly.
    graph.add_edge(
        edge.caller.fqn,
        edge.callee.fqn,
        edge_type=edge.edge_type,
        confidence=edge.confidence,
    )
