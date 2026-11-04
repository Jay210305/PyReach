"""Release regressions derived from the P8 audit and functional requirements."""

import json

import networkx as nx

from pyreach.ast.builder import ASTBuilder
from pyreach.ast.resolver import ModuleIndex
from pyreach.callgraph.engine import CallGraphEngine
from pyreach.db.connection import get_db_connection
from pyreach.osv.importer import sync_osv
from pyreach.osv.mapper import VulnerabilityMapper
from pyreach.reachability.analyzer import analyze_reachability
from tests.fixtures.advisories import stub_advisory


def record(identifier="TEST-1", package="vuln-lib", symbol="vuln_lib.risky"):
    return {
        "id": identifier,
        "modified": "2026-01-01T00:00:00Z",
        "affected": [
            {
                "package": {"ecosystem": "PyPI", "name": package},
                "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "1"}, {"fixed": "2"}]}],
                "ecosystem_specific": {"symbols": [symbol]},
            }
        ],
    }


def test_constructor_connects_to_initializer(tmp_path):
    p = tmp_path / "main.py"
    p.write_text(
        "import vuln_lib\nclass Service:\n    def __init__(self):\n"
        "        vuln_lib.risky()\ndef main():\n    Service()\n"
    )
    mods = ASTBuilder(tmp_path).build_all(
        __import__("pyreach.loaders.source", fromlist=["SourceLoader"])
        .SourceLoader(tmp_path)
        .discover()
    )
    g = CallGraphEngine(ModuleIndex(mods)).build(mods)
    result = analyze_reachability(
        g, ["main.main"], [stub_advisory()], application_imports={"vuln_lib"}
    )
    assert result[("GHSA-SYNTH-0001", "vuln_lib.risky")].status == "REACHABLE"


def test_depth_cutoff_preserves_uncertainty():
    g = nx.DiGraph()
    g.add_edges_from([("main", "middle"), ("middle", "vuln_lib.risky")])
    result = analyze_reachability(
        g, ["main"], [stub_advisory()], max_depth=1, application_imports={"vuln_lib"}
    )
    assert result[("GHSA-SYNTH-0001", "vuln_lib.risky")].status == "POTENTIALLY_REACHABLE"


def test_invalid_utf8_is_skipped(tmp_path, caplog):
    p = tmp_path / "invalid.py"
    p.write_bytes(b"\xff\xfe")
    assert ASTBuilder(tmp_path).build_file(p) is None
    assert "Failed to parse" in caplog.text


def test_incremental_directory_does_not_skip_later_file(tmp_path):
    source = tmp_path / "data"
    source.mkdir()
    for i in range(2):
        (source / f"{i}.jsonl").write_text(json.dumps(record(f"TEST-{i}")) + "\n")
    stats = sync_osv(tmp_path / "osv.db", source, incremental=True)
    assert stats.imported == 2


def test_mapper_filters_symbols_by_installed_version(tmp_path):
    data = record()
    other = record(symbol="vuln_lib.other")["affected"][0]
    other["ranges"][0]["events"] = [{"introduced": "3"}, {"fixed": "4"}]
    data["affected"].append(other)
    source = tmp_path / "data.jsonl"
    source.write_text(json.dumps(data) + "\n")
    sync_osv(tmp_path / "osv.db", source)
    with get_db_connection(tmp_path / "osv.db") as c:
        findings = VulnerabilityMapper(c).find_by_package_and_version("vuln-lib", "1.5")
        assert findings[0].affected_symbols == ["vuln_lib.risky"]


def test_multi_package_advisory_is_queryable_per_package(tmp_path):
    data = record()
    data["affected"].extend(record(package="other", symbol="other.bad")["affected"])
    source = tmp_path / "data.jsonl"
    source.write_text(json.dumps(data) + "\n")
    sync_osv(tmp_path / "osv.db", source)
    with get_db_connection(tmp_path / "osv.db") as c:
        findings = VulnerabilityMapper(c).find_by_package_and_version("other", "1.5")
        assert len(findings) == 1
        assert findings[0].affected_symbols == ["other.bad"]


def test_legacy_cache_migration_preserves_rows_and_accepts_depth_domain(tmp_path):
    import sqlite3

    from pyreach.db.connection import initialize_database

    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as c:
        c.execute(
            "CREATE TABLE reachability_results (id INTEGER PRIMARY KEY, symbol_fqn TEXT NOT NULL, "
            "entry_point_fqn TEXT NOT NULL, result TEXT, max_depth INTEGER "
            "CHECK(max_depth BETWEEN 1 AND 5), path_json TEXT, computed_at TIMESTAMP, "
            "UNIQUE(symbol_fqn,entry_point_fqn,max_depth))"
        )
        c.execute(
            "INSERT INTO reachability_results "
            "VALUES(1,'a','main','REACHABLE',5,'[]',CURRENT_TIMESTAMP)"
        )
    c.close()
    initialize_database(db)
    with sqlite3.connect(db) as c:
        assert (
            c.execute("SELECT symbol_fqn FROM reachability_results WHERE id=1").fetchone()[0] == "a"
        )
        for depth in [0, 7]:
            c.execute(
                "INSERT INTO reachability_results(symbol_fqn,entry_point_fqn,max_depth) "
                "VALUES('b','main',?)",
                (depth,),
            )

    c.close()
