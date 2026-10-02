"""S3-T8: end-to-end reachability scenarios on synthetic projects.

Proves the full pipeline (parse -> graph -> entry points -> reachability ->
classification) produces the expected verdict for five synthetic projects with
known outcomes. Deterministic: uses a stub advisory and local stub libraries,
so no network or real CVE data is required.
"""

import shutil
import time
from pathlib import Path

import pytest

from pyreach.ast.builder import ASTBuilder, ModuleAST
from pyreach.ast.resolver import ModuleIndex
from pyreach.ast.symbols import SymbolTableBuilder
from pyreach.callgraph.engine import CallGraphEngine
from pyreach.reachability.analyzer import analyze_reachability, clear_cache
from pyreach.reachability.entrypoints import EntryPointDetector
from tests.fixtures.advisories import VULN_SYMBOL, stub_advisory

PROJECTS_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "projects"

SCENARIOS = [
    ("linear_reachable", "REACHABLE"),
    ("transitive_unreachable", "NOT_REACHABLE"),
    ("dynamic_import", "POTENTIALLY_REACHABLE"),
    ("depth_limit", "NOT_REACHABLE"),
    ("package_unused", "NOT_REACHABLE"),
]

REACHABLE_PATH = ["main.main", "client.fetch", "vuln_lib.risky"]


def _copy_project(scenario: str, tmp_path: Path) -> Path:
    src = PROJECTS_DIR / scenario
    dst = tmp_path / scenario
    shutil.copytree(src, dst)
    return dst


def _run_ast_pipeline(project: Path) -> tuple[list[ModuleAST], ModuleIndex]:
    builder = ASTBuilder(module_root=project)
    modules = [m for py in sorted(project.rglob("*.py")) if (m := builder.build_file(py))]
    index = ModuleIndex(modules)
    for module in modules:
        SymbolTableBuilder(module, index.get).build()
    return modules, index


def _diagnostics(edges, entries, result) -> str:
    edge_lines = "\n".join(f"    {u} -> {v} ({d.get('edge_type')})" for u, v, d in edges)
    return (
        f"\nDiscovered entry points: {entries}\nCall graph edges:\n{edge_lines}\nResult: {result}"
    )


@pytest.mark.parametrize("scenario,expected", SCENARIOS)
def test_scenario(tmp_path: Path, scenario: str, expected: str) -> None:
    clear_cache()
    project = _copy_project(scenario, tmp_path)
    modules, index = _run_ast_pipeline(project)

    graph = CallGraphEngine(index).build(modules)
    entries = EntryPointDetector(modules).detect()
    advisory = stub_advisory()
    results = analyze_reachability(graph, entries, [advisory], max_depth=5)

    result = results[VULN_SYMBOL]
    assert result.status == expected, _diagnostics(sorted(graph.edges(data=True)), entries, result)


def test_linear_reachable_path_matches_chain(tmp_path: Path) -> None:
    clear_cache()
    project = _copy_project("linear_reachable", tmp_path)
    modules, index = _run_ast_pipeline(project)

    graph = CallGraphEngine(index).build(modules)
    entries = EntryPointDetector(modules).detect()
    result = analyze_reachability(graph, entries, [stub_advisory()], max_depth=5)[VULN_SYMBOL]

    assert result.status == "REACHABLE"
    assert REACHABLE_PATH in result.paths
    assert result.entry_points_reached == ["main.main"]


def test_not_reachable_scenarios_have_no_path(tmp_path: Path) -> None:
    for scenario in ("transitive_unreachable", "depth_limit", "package_unused"):
        clear_cache()
        project = _copy_project(scenario, tmp_path)
        modules, index = _run_ast_pipeline(project)
        graph = CallGraphEngine(index).build(modules)
        entries = EntryPointDetector(modules).detect()
        result = analyze_reachability(graph, entries, [stub_advisory()], max_depth=5)[VULN_SYMBOL]
        assert result.status == "NOT_REACHABLE", scenario
        assert result.paths == [], scenario


@pytest.mark.performance
def test_linear_reachable_performance(tmp_path: Path) -> None:
    clear_cache()
    project = _copy_project("linear_reachable", tmp_path)
    modules, index = _run_ast_pipeline(project)

    start = time.perf_counter()
    graph = CallGraphEngine(index).build(modules)
    entries = EntryPointDetector(modules).detect()
    results = analyze_reachability(graph, entries, [stub_advisory()], max_depth=5)
    elapsed = time.perf_counter() - start

    assert results[VULN_SYMBOL].status == "REACHABLE"
    assert elapsed < 2.0, f"graph build + analysis took {elapsed:.3f}s"
