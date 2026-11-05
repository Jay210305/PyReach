"""Serialization tests for SarifBuilder with codeFlows (S4-T2)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import networkx as nx
import pytest

from pyreach import __version__
from pyreach.exceptions import OutputError
from pyreach.osv.mapper import Vulnerability
from pyreach.output.sarif import (
    RULE_CATALOG,
    RULE_INDEX,
    SarifBuilder,
    load_sarif_schema,
    validate_sarif_document,
)
from pyreach.reachability.contracts import ReachabilityResult


def _vuln(
    package: str = "requests",
    symbol: str = "requests.sessions.Session.request",
    osv_id: str = "GHSA-j8r2-6x6q-8qgp",
    cve_id: str | None = "CVE-2023-32681",
    score: float | None = 7.5,
    level: str | None = "HIGH",
) -> Vulnerability:
    return Vulnerability(
        osv_id=osv_id,
        cve_id=cve_id,
        package_name=package,
        severity_score=score,
        severity_level=level,
        summary="test advisory",
        affected_symbols=[symbol],
        version_introduced=None,
        version_fixed="2.32.0",
    )


def _reachable(symbol: str = "requests.sessions.Session.request") -> ReachabilityResult:
    return ReachabilityResult(
        vulnerability=_vuln(symbol=symbol),
        status="REACHABLE",
        entry_points_reached=["main.app"],
        paths=[["main.app", "myapp.client.ApiClient.fetch_data", symbol]],
        reasoning="Static call path found from main.app (depth 2).",
    )


def _potential() -> ReachabilityResult:
    return ReachabilityResult(
        vulnerability=_vuln(),
        status="POTENTIALLY_REACHABLE",
        entry_points_reached=[],
        paths=[],
        reasoning="Dynamic import via importlib.import_module prevents static resolution",
    )


def _not_reachable() -> ReachabilityResult:
    return ReachabilityResult(
        vulnerability=_vuln(),
        status="NOT_REACHABLE",
        entry_points_reached=[],
        paths=[],
        reasoning="No call path found and package not imported.",
    )


def _graph(tmp_path: Path) -> nx.DiGraph:
    g = nx.DiGraph()
    nodes = {
        "main.app": (str(tmp_path / "src" / "myapp" / "main.py"), 10),
        "myapp.client.ApiClient.fetch_data": (str(tmp_path / "src" / "myapp" / "client.py"), 12),
        "requests.sessions.Session.request": (str(tmp_path / "src" / "myapp" / "client.py"), 24),
    }
    for fqn, (file_path, line) in nodes.items():
        g.add_node(fqn, file_path=file_path, line_number=line, node_type="FUNCTION")
    return g


def _assert_validates(doc: dict[str, object]) -> None:
    schema = load_sarif_schema()
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        print("SARIF validation failed at:", list(exc.absolute_path), exc.message)
        raise


def test_reachable_result_validates(tmp_path: Path) -> None:
    builder = SarifBuilder(
        __version__,
        tmp_path,
        graph=_graph(tmp_path),
        installed_versions={"requests": "2.31.0"},
    )
    builder.add_result(_reachable(), include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    result = doc["runs"][0]["results"][0]
    assert result["ruleId"] == "PYREACH-REACHABLE-CVE"
    assert result["level"] == "error"
    assert result["properties"]["reachability"] == "REACHABLE"
    assert result["properties"]["installedVersion"] == "2.31.0"
    assert result["properties"]["pathDepth"] == 2
    assert "codeFlows" in result


def test_potential_result_validates(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(_potential(), include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    result = doc["runs"][0]["results"][0]
    assert result["ruleId"] == "PYREACH-POTENTIAL-CVE"
    assert result["level"] == "warning"
    assert result["properties"]["reachability"] == "POTENTIALLY_REACHABLE"
    assert "reason" in result["properties"]


def test_unresolved_symbol_uses_application_file_for_report_location(tmp_path: Path) -> None:
    graph = nx.DiGraph()
    graph.add_node("main.app", file_path=str(tmp_path / "main.py"), line_number=3)
    builder = SarifBuilder(__version__, tmp_path, graph=graph)
    builder.add_result(_potential())
    result = builder.build()["runs"][0]["results"][0]
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "main.py"
    assert location["region"]["startLine"] == 3
    assert "codeFlows" not in result


def test_not_reachable_omitted_by_default(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(_not_reachable(), include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    assert doc["runs"][0]["results"] == []


def test_not_reachable_included_flag(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(_not_reachable(), include_not_reachable=True)
    doc = builder.build()
    _assert_validates(doc)
    (result,) = doc["runs"][0]["results"]
    assert result["ruleId"] == "PYREACH-NOT-REACHABLE-CVE"
    assert result["level"] == "note"


def test_codeflow_ordering(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path, graph=_graph(tmp_path))
    builder.add_result(_reachable(), include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    (flow,) = doc["runs"][0]["results"][0]["codeFlows"]
    (thread,) = flow["threadFlows"]
    kinds = [loc["kinds"][0] for loc in thread["locations"]]
    assert kinds == ["entryPoint", "call", "vulnerableCall"]
    assert len(doc["runs"][0]["results"][0]["codeFlows"]) == 1


def test_rule_index_correct(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path, graph=_graph(tmp_path))
    builder.add_result(_reachable(), include_not_reachable=False)
    builder.add_result(_potential(), include_not_reachable=False)
    builder.add_result(_not_reachable(), include_not_reachable=True)
    doc = builder.build()
    _assert_validates(doc)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert [r["id"] for r in rules] == [r.id for r in RULE_CATALOG]
    for result in doc["runs"][0]["results"]:
        assert result["ruleId"] == rules[result["ruleIndex"]]["id"]
        assert RULE_INDEX[result["ruleId"]] == result["ruleIndex"]


def test_uri_forward_slashes(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path, graph=_graph(tmp_path))
    builder.add_result(_reachable(), include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    result = doc["runs"][0]["results"][0]
    uri = result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert "\\" not in uri
    assert uri == "src/myapp/client.py"
    assert (
        result["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"]
        == "PROJECT_ROOT"
    )
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 24


def test_original_uri_base_ids(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    doc = builder.build()
    _assert_validates(doc)
    base_ids = doc["runs"][0]["originalUriBaseIds"]
    assert "PROJECT_ROOT" in base_ids
    uri = base_ids["PROJECT_ROOT"]["uri"]
    assert uri.startswith("file://")
    assert uri.endswith("/")


def test_write_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "out" / "nested" / "results.sarif"
    builder = SarifBuilder(__version__, tmp_path, graph=_graph(tmp_path))
    builder.add_result(_reachable(), include_not_reachable=False)
    builder.write(out)
    assert out.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    _assert_validates(doc)
    assert doc["runs"][0]["results"][0]["ruleId"] == "PYREACH-REACHABLE-CVE"


def test_deterministic_output(tmp_path: Path) -> None:
    high = ReachabilityResult(
        vulnerability=_vuln(
            package="b-lib",
            symbol="b_lib.func",
            osv_id="GHSA-bbbb",
            cve_id="CVE-2023-2",
            score=9.8,
            level="CRITICAL",
        ),
        status="REACHABLE",
        entry_points_reached=["main.app"],
        paths=[["main.app", "b_lib.func"]],
        reasoning="Static call path found from main.app (depth 1).",
    )
    low = ReachabilityResult(
        vulnerability=_vuln(
            package="a-lib",
            symbol="a_lib.func",
            osv_id="GHSA-aaaa",
            cve_id="CVE-2023-1",
            score=4.0,
            level="MEDIUM",
        ),
        status="POTENTIALLY_REACHABLE",
        entry_points_reached=[],
        paths=[],
        reasoning="Vulnerable package imported but exact symbol unresolved.",
    )
    first = SarifBuilder(__version__, tmp_path)
    first.add_result(low, include_not_reachable=False)
    first.add_result(high, include_not_reachable=False)
    second = SarifBuilder(__version__, tmp_path)
    second.add_result(high, include_not_reachable=False)
    second.add_result(low, include_not_reachable=False)
    first_bytes = json.dumps(first.build(), indent=2).encode()
    second_bytes = json.dumps(second.build(), indent=2).encode()
    assert first_bytes == second_bytes
    doc = first.build()
    _assert_validates(doc)
    assert [r["ruleId"] for r in doc["runs"][0]["results"]] == [
        "PYREACH-REACHABLE-CVE",
        "PYREACH-POTENTIAL-CVE",
    ]


def test_site_packages_outside_root_uses_absolute_uri(tmp_path: Path) -> None:
    g = nx.DiGraph()
    g.add_node(
        "main.app",
        file_path=str(tmp_path / "src" / "main.py"),
        line_number=5,
        node_type="FUNCTION",
    )
    g.add_node(
        "sitepkg.vuln",
        file_path="/opt/site-packages/sitepkg/mod.py",
        line_number=3,
        node_type="FUNCTION",
    )
    result = ReachabilityResult(
        vulnerability=_vuln(package="sitepkg", symbol="sitepkg.vuln"),
        status="REACHABLE",
        entry_points_reached=["main.app"],
        paths=[["main.app", "sitepkg.vuln"]],
        reasoning="Static call path found from main.app (depth 1).",
    )
    builder = SarifBuilder(__version__, tmp_path, graph=g)
    builder.add_result(result, include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    locations = doc["runs"][0]["results"][0]["codeFlows"][0]["threadFlows"][0]["locations"]
    assert locations[0]["location"]["physicalLocation"]["artifactLocation"]["uriBaseId"] == (
        "PROJECT_ROOT"
    )
    last_artifact = locations[-1]["location"]["physicalLocation"]["artifactLocation"]
    assert "uriBaseId" not in last_artifact
    assert last_artifact["uri"] == "/opt/site-packages/sitepkg/mod.py"


def test_explicit_symbol_for_multi_symbol_vulnerability(tmp_path: Path) -> None:
    vuln = _vuln(symbol="pkg.a")
    vuln.affected_symbols = ["pkg.a", "pkg.b"]
    result = ReachabilityResult(
        vulnerability=vuln,
        status="NOT_REACHABLE",
        entry_points_reached=[],
        paths=[],
        reasoning="No call path found.",
    )
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(result, include_not_reachable=True, symbol="pkg.b")
    doc = builder.build()
    _assert_validates(doc)
    result_doc = doc["runs"][0]["results"][0]
    assert result_doc["properties"]["affectedSymbol"] == "pkg.b"
    assert "pkg.b" in result_doc["message"]["text"]


def test_validation_failure_reports_element_path(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(_reachable(), include_not_reachable=False)
    doc = builder.build()
    doc["runs"][0]["results"][0]["level"] = "catastrophic"
    with pytest.raises(OutputError, match="SARIF validation failed at"):
        validate_sarif_document(doc)


def test_write_validates_before_writing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    builder.add_result(_reachable(), include_not_reachable=False)
    invalid = json.loads(json.dumps(builder.build()))
    invalid["runs"][0]["results"][0]["level"] = "catastrophic"
    monkeypatch.setattr(builder, "build", lambda: invalid)
    out = tmp_path / "bad.sarif"
    with pytest.raises(OutputError, match="SARIF validation failed"):
        builder.write(out)
    assert not out.exists()


def test_single_node_path_carries_both_kinds(tmp_path: Path) -> None:
    g = nx.DiGraph()
    g.add_node(
        "pkg.func",
        file_path=str(tmp_path / "src" / "pkg.py"),
        line_number=1,
        node_type="FUNCTION",
    )
    result = ReachabilityResult(
        vulnerability=_vuln(package="pkg", symbol="pkg.func"),
        status="REACHABLE",
        entry_points_reached=["pkg.func"],
        paths=[["pkg.func"]],
        reasoning="Static call path found from pkg.func (depth 0).",
    )
    builder = SarifBuilder(__version__, tmp_path, graph=g)
    builder.add_result(result, include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    (loc,) = doc["runs"][0]["results"][0]["codeFlows"][0]["threadFlows"][0]["locations"]
    assert sorted(loc["kinds"]) == ["entryPoint", "vulnerableCall"]


def test_relative_path_outside_root_has_no_base_id(tmp_path: Path) -> None:
    g = nx.DiGraph()
    g.add_node("pkg.func", file_path="../shared/pkg.py", line_number=7, node_type="FUNCTION")
    result = ReachabilityResult(
        vulnerability=_vuln(package="pkg", symbol="pkg.func"),
        status="POTENTIALLY_REACHABLE",
        entry_points_reached=[],
        paths=[],
        reasoning="Vulnerable package imported but exact symbol unresolved.",
    )
    builder = SarifBuilder(__version__, tmp_path, graph=g)
    builder.add_result(result, include_not_reachable=False)
    doc = builder.build()
    _assert_validates(doc)
    artifact = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]
    assert artifact["uri"] == "../shared/pkg.py"
    assert "uriBaseId" not in artifact


@pytest.mark.performance
def test_builder_scales_to_many_results(tmp_path: Path) -> None:
    builder = SarifBuilder(__version__, tmp_path)
    for i in range(500):
        vuln = _vuln(package=f"pkg-{i:03d}", symbol=f"pkg_{i}.func", osv_id=f"GHSA-{i:04d}")
        builder.add_result(
            ReachabilityResult(
                vulnerability=vuln,
                status="NOT_REACHABLE",
                entry_points_reached=[],
                paths=[],
                reasoning="No call path found.",
            ),
            include_not_reachable=True,
        )
    doc = builder.build()
    assert len(doc["runs"][0]["results"]) == 500
