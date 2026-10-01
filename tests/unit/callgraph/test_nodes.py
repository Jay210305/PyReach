import dataclasses

import pytest

from pyreach.callgraph.nodes import CGNode, add_cgnode
from pyreach.exceptions import AnalysisError

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]


def test_cgnode_frozen() -> None:
    n = CGNode(fqn="pkg.mod.func", file_path="pkg/mod.py", line_number=10, node_type="FUNCTION")
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.fqn = "other"  # type: ignore[misc]


def test_cgnode_hashable() -> None:
    n1 = CGNode(fqn="pkg.a", node_type="FUNCTION")
    n2 = CGNode(fqn="pkg.b", node_type="CLASS")
    s = {n1, n2}
    d = {n1: 1, n2: 2}
    assert len(s) == 2
    assert d[n1] == 1


def test_cgnode_validates_type() -> None:
    with pytest.raises(AnalysisError):
        CGNode(fqn="x", node_type="BAD")  # type: ignore[arg-type]
    with pytest.raises(AnalysisError):
        CGNode(fqn="", node_type="FUNCTION")


def test_cgnode_sort_order() -> None:
    nodes = [
        CGNode(fqn="z.mod.func"),
        CGNode(fqn="a.mod.func"),
        CGNode(fqn="m.mod.func"),
    ]
    assert [n.fqn for n in sorted(nodes)] == ["a.mod.func", "m.mod.func", "z.mod.func"]


def test_cgnode_is_lambda_and_is_callable() -> None:
    lam = CGNode(fqn="<lambda>:pkg/mod.py:42", node_type="LAMBDA")
    func = CGNode(fqn="pkg.mod.func", node_type="FUNCTION")
    meth = CGNode(fqn="pkg.Mod.method", node_type="METHOD")
    cls = CGNode(fqn="pkg.Mod", node_type="CLASS")
    assert lam.is_lambda is True
    assert func.is_lambda is False
    assert func.is_callable is True
    assert meth.is_callable is True
    assert lam.is_callable is True
    assert cls.is_callable is False
    assert cls.is_lambda is False


def test_cgnode_str() -> None:
    n = CGNode(fqn="pkg.mod.func")
    assert str(n) == "pkg.mod.func"


def test_node_row_roundtrip() -> None:
    n = CGNode(fqn="pkg.mod.func", file_path="pkg/mod.py", line_number=42, node_type="METHOD")
    row = n.to_row()
    assert row == {
        "node_fqn": "pkg.mod.func",
        "file_path": "pkg/mod.py",
        "line_number": 42,
        "node_type": "METHOD",
    }
    m = CGNode.from_row(row)
    assert m == n


def test_node_row_roundtrip_with_nulls() -> None:
    n = CGNode(fqn="pkg.mod.func")
    row = n.to_row()
    assert row["file_path"] is None
    assert row["line_number"] is None
    m = CGNode.from_row(row)
    assert m == n


def test_add_cgnode_uses_fqn_string_key() -> None:
    if nx is None:  # pragma: no cover
        pytest.skip("networkx not installed")
    G = nx.DiGraph()
    n = CGNode(fqn="pkg.mod.func", file_path="pkg/mod.py", line_number=10, node_type="FUNCTION")
    add_cgnode(G, n)
    assert "pkg.mod.func" in G
    assert G.nodes["pkg.mod.func"]["node"] == n
    assert G.nodes["pkg.mod.func"]["node_type"] == "FUNCTION"
    # string key, not object key
    assert n not in G  # type: ignore[operator]
