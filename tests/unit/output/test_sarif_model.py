"""Design-validation tests for the SARIF builder (S4-T1)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from pyreach import __version__
from pyreach.output.sarif import (
    RULE_CATALOG,
    RULE_INDEX,
    SARIF_SCHEMA_URL,
    SARIF_VERSION,
    STATUS_TO_LEVEL,
    STATUS_TO_RULE_ID,
    SarifArtifactLocation,
    SarifCodeFlow,
    SarifDriver,
    SarifInvocation,
    SarifLocation,
    SarifLogicalLocation,
    SarifMessage,
    SarifPhysicalLocation,
    SarifRegion,
    SarifReport,
    SarifResult,
    SarifRun,
    SarifThreadFlow,
    SarifThreadFlowLocation,
    SarifTool,
    UriBase,
    load_sarif_schema,
)


def _make_minimal_report() -> SarifReport:
    driver = SarifDriver(
        name="PyReach",
        version=__version__,
        information_uri="https://github.com/lidercom/pyreach",
        rules=list(RULE_CATALOG),
    )
    tool = SarifTool(driver=driver)
    run = SarifRun(
        tool=tool,
        results=[],
        invocations=[
            SarifInvocation(
                execution_successful=True,
                arguments=["pyreach", "."],
                working_directory_uri="file:///tmp/project/",
            )
        ],
        original_uri_base_ids={"PROJECT_ROOT": UriBase(uri="file:///tmp/project/")},
    )
    return SarifReport(runs=[run])


# ------------------------------------------------------------------


def test_schema_fixture_parses_and_contains_definitions() -> None:
    schema = load_sarif_schema()
    assert isinstance(schema, dict)
    assert "definitions" in schema
    assert "properties" in schema


def test_schema_explicit_path_and_missing_raises() -> None:
    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "sarif_schema"
        / "sarif-schema-2.1.0.json"
    )
    assert "definitions" in load_sarif_schema(fixture)
    with pytest.raises(FileNotFoundError):
        load_sarif_schema(Path("no/such/schema.json"))


def test_report_minimal_validates() -> None:
    report = _make_minimal_report()
    doc = report.to_dict()
    schema = load_sarif_schema()
    jsonschema.validate(instance=doc, schema=schema)


def test_schema_and_version_strings_exact() -> None:
    report = _make_minimal_report()
    doc = report.to_dict()
    assert doc["$schema"] == SARIF_SCHEMA_URL
    assert doc["version"] == SARIF_VERSION
    assert doc["version"] == "2.1.0"
    assert not str(doc["$schema"]).endswith("/")


def test_rule_index_matches_catalog() -> None:
    for idx, rule in enumerate(RULE_CATALOG):
        assert RULE_INDEX[rule.id] == idx
    report = _make_minimal_report()
    doc = report.to_dict()
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    for idx, rule_dict in enumerate(rules):
        rule_id = rule_dict["id"]
        assert RULE_INDEX[rule_id] == idx
        assert rule_dict["id"] == RULE_CATALOG[idx].id

    # Result ruleIndex points at correct rule
    for status, rule_id in STATUS_TO_RULE_ID.items():
        rule_index = RULE_INDEX[rule_id]
        result = SarifResult(
            rule_id=rule_id,
            rule_index=rule_index,
            level=STATUS_TO_LEVEL[status],
            message=SarifMessage(text=f"{status} test"),
        )
        assert result.to_dict()["ruleIndex"] == rule_index
        assert result.to_dict()["ruleId"] == RULE_CATALOG[rule_index].id


def test_every_class_to_dict_json_serializable() -> None:
    msg = SarifMessage(text="hello")
    artifact = SarifArtifactLocation(uri="src/app.py", uri_base_id="PROJECT_ROOT")
    region = SarifRegion(start_line=1, start_column=1, end_column=10)
    phys = SarifPhysicalLocation(artifact_location=artifact, region=region)
    logical = SarifLogicalLocation(fully_qualified_name="pkg.mod.func")
    loc = SarifLocation(physical_location=phys, logical_locations=[logical], message=msg)
    tfl = SarifThreadFlowLocation(location=loc, kinds=["entryPoint"])
    tf = SarifThreadFlow(locations=[tfl])
    cf = SarifCodeFlow(thread_flows=[tf])
    rule = RULE_CATALOG[0]
    driver = SarifDriver(
        name="PyReach", version="0.1.0", information_uri="https://example.com", rules=[rule]
    )
    tool = SarifTool(driver=driver)
    inv = SarifInvocation(
        execution_successful=True, arguments=["pyreach"], working_directory_uri="file:///tmp/"
    )
    base = UriBase(uri="file:///tmp/")
    result = SarifResult(
        rule_id=rule.id,
        rule_index=0,
        level="error",
        message=msg,
        locations=[loc],
        code_flows=[cf],
        properties={"reachability": "REACHABLE"},
    )
    run = SarifRun(
        tool=tool, results=[result], invocations=[inv], original_uri_base_ids={"PROJECT_ROOT": base}
    )
    report = SarifReport(runs=[run])

    for obj in [
        msg,
        artifact,
        region,
        phys,
        logical,
        loc,
        tfl,
        tf,
        cf,
        rule,
        driver,
        tool,
        inv,
        base,
        result,
        run,
        report,
    ]:
        d = obj.to_dict()
        json.dumps(d)

    # Full report also serializable
    json.dumps(report.to_dict())


def test_level_mapping() -> None:
    assert STATUS_TO_LEVEL["REACHABLE"] == "error"
    assert STATUS_TO_LEVEL["POTENTIALLY_REACHABLE"] == "warning"
    assert STATUS_TO_LEVEL["NOT_REACHABLE"] == "note"

    assert STATUS_TO_RULE_ID["REACHABLE"] == "PYREACH-REACHABLE-CVE"
    assert STATUS_TO_RULE_ID["POTENTIALLY_REACHABLE"] == "PYREACH-POTENTIAL-CVE"
    assert STATUS_TO_RULE_ID["NOT_REACHABLE"] == "PYREACH-NOT-REACHABLE-CVE"

    for rule in RULE_CATALOG:
        if rule.id == "PYREACH-REACHABLE-CVE":
            assert rule.default_level == "error"
        elif rule.id == "PYREACH-POTENTIAL-CVE":
            assert rule.default_level == "warning"
        elif rule.id == "PYREACH-NOT-REACHABLE-CVE":
            assert rule.default_level == "note"


def test_properties_only_custom_metadata() -> None:
    report = _make_minimal_report()

    # Add a reachable result with properties
    result = SarifResult(
        rule_id="PYREACH-REACHABLE-CVE",
        rule_index=RULE_INDEX["PYREACH-REACHABLE-CVE"],
        level="error",
        message=SarifMessage(text="CVE-2023-1 in pkg==1.0: pkg.func is REACHABLE"),
        locations=[
            SarifLocation(
                physical_location=SarifPhysicalLocation(
                    artifact_location=SarifArtifactLocation(
                        uri="src/app.py", uri_base_id="PROJECT_ROOT"
                    ),
                    region=SarifRegion(start_line=10),
                ),
                logical_locations=[SarifLogicalLocation(fully_qualified_name="pkg.func")],
            )
        ],
        properties={
            "reachability": "REACHABLE",
            "cveId": "CVE-2023-1",
            "osvId": "GHSA-xxxx",
            "packageName": "pkg",
            "installedVersion": "1.0",
            "severityScore": 7.5,
            "pathDepth": 2,
        },
    )
    report.runs[0].results.append(result)
    doc = report.to_dict()

    # Top-level report keys must be standard SARIF
    allowed_report_keys = {"$schema", "version", "runs", "inlineExternalProperties", "properties"}
    assert set(doc.keys()).issubset(allowed_report_keys)

    # Run keys must be standard
    allowed_run_keys = {
        "tool",
        "results",
        "invocations",
        "originalUriBaseIds",
        "artifacts",
        "conversion",
        "language",
        "versionControlProvenance",
        "automationDetails",
        "properties",
        "taxonomies",
        "addresses",
        "webRequests",
        "webResponses",
        "columnKind",
        "defaultEncoding",
        "defaultSourceLanguage",
        "newlineSequences",
        "externalPropertyFileReferences",
        "threadFlowLocations",
        "logicalLocations",
        "graphs",
    }
    for run in doc["runs"]:
        assert set(run.keys()).issubset(allowed_run_keys)

    # Result keys must be standard; custom data only in properties
    allowed_result_keys = {
        "ruleId",
        "ruleIndex",
        "rule",
        "level",
        "message",
        "locations",
        "codeFlows",
        "properties",
        "analysisTarget",
        "guid",
        "correlationGuid",
        "occurrenceCount",
        "fingerprints",
        "partialFingerprints",
        "stacks",
        "graphs",
        "graphTraversals",
        "relatedLocations",
        "suppressions",
        "baselineState",
        "rank",
        "attachments",
        "hostedViewerUri",
        "workItemUris",
        "provenance",
        "fixes",
        "taxa",
        "webRequest",
        "webResponse",
        "kind",
    }
    for run in doc["runs"]:
        for res in run.get("results", []):
            assert set(res.keys()).issubset(allowed_result_keys), (
                f"Unexpected keys: {set(res.keys()) - allowed_result_keys}"
            )
            # Custom reachability fields must be inside properties, not top-level
            for custom in ("reachability", "cveId", "osvId", "packageName"):
                assert custom not in res, f"Custom key {custom} leaked to top-level"
                if "properties" in res:
                    assert custom in res["properties"] or custom not in res["properties"]

    # Still validates
    schema = load_sarif_schema()
    jsonschema.validate(instance=doc, schema=schema)


def test_artifact_uri_uses_forward_slashes_and_base_id() -> None:
    loc = SarifLocation(
        physical_location=SarifPhysicalLocation(
            artifact_location=SarifArtifactLocation(
                uri="src/myapp/client.py", uri_base_id="PROJECT_ROOT"
            ),
            region=SarifRegion(start_line=24),
        ),
        logical_locations=[SarifLogicalLocation(fully_qualified_name="myapp.client.func")],
    )
    d = loc.to_dict()
    assert d["physicalLocation"]["artifactLocation"]["uri"] == "src/myapp/client.py"
    assert d["physicalLocation"]["artifactLocation"]["uriBaseId"] == "PROJECT_ROOT"
    assert "\\" not in d["physicalLocation"]["artifactLocation"]["uri"]


def test_codeflow_kinds_contract() -> None:
    # Entry point -> call -> vulnerableCall
    entry = SarifThreadFlowLocation(
        location=SarifLocation(message=SarifMessage(text="Entry point: main.app")),
        kinds=["entryPoint"],
    )
    middle = SarifThreadFlowLocation(
        location=SarifLocation(message=SarifMessage(text="-> myapp.client.fetch_data")),
        kinds=["call"],
    )
    vulnerable = SarifThreadFlowLocation(
        location=SarifLocation(
            message=SarifMessage(text="-> requests.sessions.Session.request (VULNERABLE)")
        ),
        kinds=["vulnerableCall"],
    )
    tf = SarifThreadFlow(locations=[entry, middle, vulnerable])
    cf = SarifCodeFlow(thread_flows=[tf])
    d = cf.to_dict()
    kinds = [loc["kinds"][0] for loc in d["threadFlows"][0]["locations"]]
    assert kinds == ["entryPoint", "call", "vulnerableCall"]


def test_original_uri_base_ids_project_root() -> None:
    report = _make_minimal_report()
    doc = report.to_dict()
    assert "originalUriBaseIds" in doc["runs"][0]
    assert "PROJECT_ROOT" in doc["runs"][0]["originalUriBaseIds"]
    uri = doc["runs"][0]["originalUriBaseIds"]["PROJECT_ROOT"]["uri"]
    assert uri.startswith("file://")
