"""CGNode — immutable graph node per spec §3.3 and S3-T1 Decision B."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pyreach.exceptions import AnalysisError

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]

NodeType = Literal["FUNCTION", "METHOD", "CLASS", "LAMBDA"]

_VALID_NODE_TYPES: set[str] = {"FUNCTION", "METHOD", "CLASS", "LAMBDA"}


@dataclass(frozen=True, order=True)
class CGNode:
    fqn: str
    file_path: str | None = None
    line_number: int | None = None
    node_type: NodeType = "FUNCTION"

    def __post_init__(self) -> None:
        if self.node_type not in _VALID_NODE_TYPES:
            raise AnalysisError(f"Invalid node_type: {self.node_type!r}")
        if not self.fqn:
            raise AnalysisError("CGNode fqn must be non-empty")

    @property
    def is_lambda(self) -> bool:
        return self.node_type == "LAMBDA"

    @property
    def is_callable(self) -> bool:
        return self.node_type in {"FUNCTION", "METHOD", "LAMBDA"}

    def __str__(self) -> str:
        return self.fqn

    def to_row(self) -> dict[str, object]:
        return {
            "node_fqn": self.fqn,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "node_type": self.node_type,
        }

    @classmethod
    def from_row(cls, row: dict[str, object]) -> CGNode:
        return cls(
            fqn=str(row["node_fqn"]),
            file_path=row.get("file_path") if row.get("file_path") is not None else None,  # type: ignore[arg-type]
            line_number=row.get("line_number") if row.get("line_number") is not None else None,  # type: ignore[arg-type]
            node_type=row["node_type"],  # type: ignore[arg-type]
        )


def add_cgnode(graph: object, node: CGNode) -> None:
    if nx is None:  # pragma: no cover
        raise AnalysisError("networkx not installed")
    assert isinstance(graph, nx.DiGraph)
    graph.add_node(
        node.fqn,
        node=node,
        file_path=node.file_path,
        line_number=node.line_number,
        node_type=node.node_type,
    )
