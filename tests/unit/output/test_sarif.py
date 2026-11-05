"""Schema, locations, determinism and report-write failure contracts."""

import json
from pathlib import Path

import jsonschema
import networkx as nx
import pytest

from pyreach.exceptions import OutputError
from pyreach.output.sarif import SarifBuilder, write_report
from pyreach.output.summary import summarize
from pyreach.reachability.contracts import ReachabilityResult
from tests.fixtures.advisories import stub_advisory

SCHEMA = json.loads((Path(__file__).parents[2] / "fixtures/sarif-schema-2.1.0.json").read_text())


@pytest.mark.parametrize("status", ["REACHABLE", "POTENTIALLY_REACHABLE", "NOT_REACHABLE"])
def test_schema_locations_and_codeflows(tmp_path, status):
    g = nx.DiGraph()
    g.add_node("app.main", file_path=str(tmp_path / "app.py"), line_number=3)
    g.add_node("vuln_lib.risky", file_path=str(tmp_path.parent / "external.py"), line_number=None)
    b = SarifBuilder("0.1.0", tmp_path, g)
    r = ReachabilityResult(
        stub_advisory(),
        status,
        ["app.main"],
        [["app.main", "vuln_lib.risky"]] if status == "REACHABLE" else [],
        "test",
    )
    b.add_result(r, include_not_reachable=True)
    doc = b.build()
    jsonschema.validate(doc, SCHEMA)
    row = doc["runs"][0]["results"][0]
    assert "region" not in row["locations"][0]["physicalLocation"]
    if status == "REACHABLE":
        loc = row["codeFlows"][0]["threadFlows"][0]["locations"]
        assert loc[0]["kinds"] == ["entryPoint"] and loc[-1]["kinds"] == ["vulnerableCall"]
    assert b.build() == doc
    b.write(tmp_path / "report.sarif")


def test_not_reachable_is_filtered_and_unknown_location_has_no_fake_line(tmp_path):
    b = SarifBuilder("0.1.0", tmp_path)
    r = ReachabilityResult(stub_advisory(), "NOT_REACHABLE", [], [], "none")
    b.add_result(r)
    assert b.build()["runs"][0]["results"] == []
    assert "physicalLocation" not in b.location("unknown")
    assert summarize({("X", "foo"): r})["summary"]["reduction_percent"] == 100


def test_write_failure_has_domain_error(tmp_path):
    with pytest.raises(OutputError):
        write_report(tmp_path, {"x": 1})


def test_advisory_with_one_reachable_symbol_is_never_counted_discarded():
    v = stub_advisory()
    results = {
        (v.osv_id, "a"): ReachabilityResult(v, "NOT_REACHABLE", [], [], "none"),
        (v.osv_id, "b"): ReachabilityResult(v, "REACHABLE", ["main"], [["main", "b"]], "path"),
    }
    assert summarize(results)["summary"]["reduction_percent"] == 0
