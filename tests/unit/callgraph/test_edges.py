import pytest

from pyreach.callgraph.edges import CGEdge, add_cgedge
from pyreach.callgraph.nodes import CGNode
from pyreach.exceptions import AnalysisError

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]


def _node(fqn: str) -> CGNode:
    return CGNode(fqn=fqn)


def test_cgedge_validates_confidence() -> None:
    a = _node("pkg.a")
    b = _node("pkg.b")
    with pytest.raises(AnalysisError):
        CGEdge(caller=a, callee=b, edge_type="STATIC", confidence=-0.1)
    with pytest.raises(AnalysisError):
        CGEdge(caller=a, callee=b, edge_type="STATIC", confidence=1.1)
    # boundaries ok
    CGEdge(caller=a, callee=b, edge_type="STATIC", confidence=0.0)
    CGEdge(caller=a, callee=b, edge_type="DYNAMIC", confidence=1.0)


def test_cgedge_validates_type() -> None:
    a = _node("pkg.a")
    b = _node("pkg.b")
    with pytest.raises(AnalysisError):
        CGEdge(caller=a, callee=b, edge_type="BAD")  # type: ignore[arg-type]


def test_cgedge_is_dynamic() -> None:
    a = _node("pkg.a")
    b = _node("pkg.b")
    assert CGEdge(caller=a, callee=b, edge_type="DYNAMIC").is_dynamic is True
    assert CGEdge(caller=a, callee=b, edge_type="STATIC").is_dynamic is False
    assert CGEdge(caller=a, callee=b, edge_type="INHERITANCE").is_dynamic is False
    assert CGEdge(caller=a, callee=b, edge_type="IMPORT").is_dynamic is False


def test_cgedge_frozen() -> None:
    import dataclasses

    a = _node("pkg.a")
    b = _node("pkg.b")
    e = CGEdge(caller=a, callee=b, edge_type="STATIC", confidence=1.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.confidence = 0.5  # type: ignore[misc]


def test_cgedge_hashable_via_fqn() -> None:
    a = _node("pkg.a")
    b = _node("pkg.b")
    e = CGEdge(caller=a, callee=b, edge_type="STATIC")
    # CGEdge is frozen, so usable as dict key via its CGNode fields
    d = {e: 1}
    assert d[e] == 1


def test_edge_row_roundtrip_via_graph() -> None:
    if nx is None:  # pragma: no cover
        pytest.skip("networkx not installed")
    G = nx.DiGraph()
    a = CGNode(fqn="pkg.a", node_type="FUNCTION")
    b = CGNode(fqn="pkg.b", node_type="FUNCTION")
    # need nodes for FK, but edges store fqn strings per Decision B
    from pyreach.callgraph.nodes import add_cgnode

    add_cgnode(G, a)
    add_cgnode(G, b)
    e = CGEdge(caller=a, callee=b, edge_type="STATIC", confidence=1.0)
    add_cgedge(G, e)
    assert G.has_edge("pkg.a", "pkg.b")
    assert G["pkg.a"]["pkg.b"]["edge_type"] == "STATIC"
    assert G["pkg.a"]["pkg.b"]["confidence"] == 1.0


def test_add_cgedge_dynamic_confidence() -> None:
    if nx is None:  # pragma: no cover
        pytest.skip("networkx not installed")
    G = nx.DiGraph()
    a = CGNode(fqn="pkg.a")
    b = CGNode(fqn="pkg.b")
    from pyreach.callgraph.nodes import add_cgnode

    add_cgnode(G, a)
    add_cgnode(G, b)
    e = CGEdge(caller=a, callee=b, edge_type="DYNAMIC", confidence=0.5)
    add_cgedge(G, e)
    assert G["pkg.a"]["pkg.b"]["confidence"] == 0.5
