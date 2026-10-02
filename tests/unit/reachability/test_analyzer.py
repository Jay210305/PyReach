"""Tests for S3-T5 bounded reachability BFS with memoization."""

import time
import tracemalloc

import networkx as nx
import pytest

import pyreach.reachability.analyzer as analyzer_mod
from pyreach.parsers.osv_json import Vulnerability
from pyreach.reachability.analyzer import (
    ReachabilityResult,
    analyze_reachability,
    clear_cache,
)
from pyreach.reachability.contracts import MAX_PATHS


def _make_vuln(package: str = "pkg", symbols: tuple[str, ...] = ("pkg.func",)) -> Vulnerability:
    return Vulnerability(
        osv_id="TEST-1",
        cve_id=None,
        package_name=package,
        severity_score=None,
        severity_level=None,
        summary="test advisory",
        affected_symbols=list(symbols),
        version_introduced=None,
        version_fixed=None,
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def test_reachable_direct() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("main", "a"), ("a", "pkg.func")])
    result = analyze_reachability(graph, ["main"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "REACHABLE"
    assert ["main", "a", "pkg.func"] in result.paths
    assert result.entry_points_reached == ["main"]


def test_not_reachable() -> None:
    graph = nx.DiGraph()
    graph.add_node("main")
    graph.add_node("pkg.func")
    result = analyze_reachability(graph, ["main"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "NOT_REACHABLE"
    assert result.paths == []


def test_potentially_reachable_dynamic() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "a")
    graph.add_edge("a", "<DYNAMIC>", edge_type="DYNAMIC")
    graph.add_node("pkg.func")
    result = analyze_reachability(graph, ["main"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "POTENTIALLY_REACHABLE"


def test_depth_limit_exceeded() -> None:
    graph = nx.DiGraph()
    for i in range(6):
        graph.add_edge(f"n{i}", f"n{i + 1}")
    vuln = _make_vuln(package="n6", symbols=("n6",))
    result = analyze_reachability(graph, ["n0"], [vuln], max_depth=5)["n6"]
    assert result.status == "NOT_REACHABLE"
    assert "depth limit" in result.reasoning


def test_cycle_handling() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "a"), ("a", "pkg.func")])
    result = analyze_reachability(graph, ["a"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "REACHABLE"


def test_pure_cycle_not_reachable() -> None:
    graph = nx.DiGraph()
    graph.add_edges_from([("a", "b"), ("b", "a")])
    graph.add_node("pkg.func")
    result = analyze_reachability(graph, ["a"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "NOT_REACHABLE"


def test_memoization(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, int]] = []
    original = analyzer_mod._traverse_uncached

    def spy(graph: nx.DiGraph, entry: str, target: str, max_depth: int):
        calls.append((entry, target, max_depth))
        return original(graph, entry, target, max_depth)

    monkeypatch.setattr(analyzer_mod, "_traverse_uncached", spy)
    graph = nx.DiGraph()
    graph.add_edge("main", "pkg.func")
    analyzer_mod._traverse(graph, "main", "pkg.func", 5)
    analyzer_mod._traverse(graph, "main", "pkg.func", 5)
    assert len(calls) == 1


def test_package_imported_fallback() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "requests.get")
    vuln = _make_vuln(package="requests", symbols=("requests.sessions.Session.request",))
    result = analyze_reachability(graph, ["main"], [vuln], max_depth=5)[
        "requests.sessions.Session.request"
    ]
    assert result.status == "POTENTIALLY_REACHABLE"
    assert "imported" in result.reasoning


def test_package_not_imported() -> None:
    graph = nx.DiGraph()
    graph.add_node("main")
    vuln = _make_vuln(package="requests", symbols=("requests.sessions.Session.request",))
    result = analyze_reachability(graph, ["main"], [vuln], max_depth=5)[
        "requests.sessions.Session.request"
    ]
    assert result.status == "NOT_REACHABLE"


def test_performance_100_nodes() -> None:
    graph = nx.DiGraph()
    for i in range(99):
        graph.add_edge(f"n{i}", f"n{i + 1}")
    vuln = _make_vuln(symbols=("n99",))
    tracemalloc.start()
    start = time.perf_counter()
    result = analyze_reachability(graph, ["n0"], [vuln], max_depth=100)["n99"]
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert result.status == "REACHABLE"
    assert elapsed < 0.1
    assert peak < 20 * 1024 * 1024


def test_paths_are_short_and_bounded() -> None:
    graph = nx.DiGraph()
    entries = [f"e{i}" for i in range(10)]
    for entry in entries:
        graph.add_edge(entry, "mid")
    graph.add_edge("mid", "pkg.func")
    result = analyze_reachability(graph, entries, [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "REACHABLE"
    assert len(result.paths) <= MAX_PATHS
    assert result.entry_points_reached == sorted(entries)


def test_entry_is_target() -> None:
    graph = nx.DiGraph()
    graph.add_node("pkg.func")
    result = analyze_reachability(graph, ["pkg.func"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "REACHABLE"
    assert result.paths == [["pkg.func"]]


def test_negative_max_depth_raises() -> None:
    graph = nx.DiGraph()
    with pytest.raises(ValueError):
        analyze_reachability(graph, ["main"], [_make_vuln()], max_depth=-1)


def test_multiple_symbols_keyed_by_fqn() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "pkg.a")
    graph.add_node("pkg.b")
    vuln = _make_vuln(symbols=("pkg.a", "pkg.b"))
    results = analyze_reachability(graph, ["main"], [vuln], max_depth=5)
    assert set(results) == {"pkg.a", "pkg.b"}
    assert results["pkg.a"].status == "REACHABLE"
    assert results["pkg.b"].status == "NOT_REACHABLE"


def test_result_is_reachability_result_type() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "pkg.func")
    result = analyze_reachability(graph, ["main"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert isinstance(result, ReachabilityResult)
    assert result.vulnerability.osv_id == "TEST-1"


def test_entry_not_in_graph() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "pkg.func")
    result = analyze_reachability(graph, ["missing"], [_make_vuln()], max_depth=5)["pkg.func"]
    assert result.status == "NOT_REACHABLE"
    assert result.entry_points_reached == []


def test_depth_exceeded_with_tail_nodes() -> None:
    graph = nx.DiGraph()
    for i in range(7):
        graph.add_edge(f"n{i}", f"n{i + 1}")
    graph.add_node("n8")
    vuln = _make_vuln(package="n8", symbols=("n8",))
    result = analyze_reachability(graph, ["n0"], [vuln], max_depth=5)["n8"]
    assert result.status == "NOT_REACHABLE"
    assert "depth limit" in result.reasoning


def test_package_cache_reuse_two_symbols() -> None:
    graph = nx.DiGraph()
    graph.add_edge("main", "requests.get")
    vuln = _make_vuln(
        package="requests",
        symbols=("requests.sessions.Session.request", "requests.sessions.Session.close"),
    )
    results = analyze_reachability(graph, ["main"], [vuln], max_depth=5)
    assert results["requests.sessions.Session.request"].status == "POTENTIALLY_REACHABLE"
    assert results["requests.sessions.Session.close"].status == "POTENTIALLY_REACHABLE"
