"""Unit tests for the CLI parser, pipeline steps and exit codes (S4-T3)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import zipfile
from pathlib import Path

import networkx as nx
import pytest

from pyreach import __version__
from pyreach.cli import (
    ExitCode,
    _symbol_module_file,
    build_json_document,
    build_parser,
    compute_exit_code,
    format_text,
    load_vulnerabilities,
    main,
    parse_manifest,
    run_scan,
)
from pyreach.db.connection import initialize_database
from pyreach.exceptions import ConfigError, OSVError
from pyreach.osv.mapper import Vulnerability
from pyreach.parsers.manifest import Dependency
from pyreach.reachability.contracts import ReachabilityResult


def _seed_db(db_path: Path) -> None:
    initialize_database(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "INSERT INTO advisories (osv_id, cve_id, package_name, ecosystem,"
            " severity_score, severity_level, summary)"
            " VALUES ('GHSA-SYNTH-0001','CVE-2026-00001','vuln-lib','PyPI',9.8,"
            " 'CRITICAL','synthetic')"
        )
        conn.execute(
            "INSERT INTO affected_symbols (advisory_id, symbol_fqn, version_introduced,"
            " version_fixed, version_fixed_inclusive)"
            " VALUES (?, 'vuln_lib.risky', '1.0.0', '2.0.0', 0)",
            (cur.lastrowid,),
        )
        conn.commit()
    finally:
        conn.close()


def _reachable_result() -> ReachabilityResult:
    return ReachabilityResult(
        vulnerability=Vulnerability(
            osv_id="GHSA-SYNTH-0001",
            cve_id="CVE-2026-00001",
            package_name="vuln-lib",
            severity_score=9.8,
            severity_level="CRITICAL",
            summary="synthetic",
            affected_symbols=["vuln_lib.risky"],
            version_introduced="1.0.0",
            version_fixed="2.0.0",
        ),
        status="REACHABLE",
        entry_points_reached=["main.main"],
        paths=[["main.main", "client.fetch", "vuln_lib.risky"]],
        reasoning="Static call path found from main.main (depth 2).",
    )


def _potential_result() -> ReachabilityResult:
    result = _reachable_result()
    result.status = "POTENTIALLY_REACHABLE"
    result.entry_points_reached = []
    result.paths = []
    return result


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _ns(**overrides: object) -> argparse.Namespace:
    base = {
        "project_path": None,
        "manifest": None,
        "db_path": None,
        "output": None,
        "entry_point": None,
        "max_depth": None,
        "include_potentially": False,
        "include_all": False,
        "no_fail": False,
        "format": "sarif",
        "exclude": None,
        "cache": True,
        "verbose": False,
        "quiet": True,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------


def test_parser_defaults_use_sentinels() -> None:
    args = build_parser().parse_args(["some-project"])
    assert args.project_path == "some-project"
    assert args.manifest is None
    assert args.db_path is None
    assert args.output is None
    assert args.max_depth is None
    assert args.entry_point is None
    assert args.exclude is None
    assert args.format == "sarif"
    assert args.cache is True


def test_parser_repeatable_and_choices() -> None:
    args = build_parser().parse_args(
        ["proj", "-e", "a.b", "-e", "c.d", "--exclude", "tests/", "-f", "text", "-k", "3"]
    )
    assert args.entry_point == ["a.b", "c.d"]
    assert args.exclude == ["tests/"]
    assert args.format == "text"
    assert args.max_depth == 3


def test_parser_version_reports_pyreach_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert f"PyReach {__version__}" in capsys.readouterr().out


def test_project_path_optional_for_version() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0


# ------------------------------------------------------------------
# Exit codes
# ------------------------------------------------------------------


def test_exit_code_empty_results_is_zero() -> None:
    assert compute_exit_code([], _ns()) == ExitCode.SUCCESS


def test_exit_code_reachable_is_one() -> None:
    assert compute_exit_code([_reachable_result()], _ns()) == ExitCode.FINDINGS


def test_exit_code_potential_zero_by_default() -> None:
    assert compute_exit_code([_potential_result()], _ns()) == ExitCode.SUCCESS


def test_exit_code_potential_one_with_flag() -> None:
    assert compute_exit_code([_potential_result()], _ns(include_potentially=True)) == (
        ExitCode.FINDINGS
    )


def test_exit_code_no_fail_wins_over_findings() -> None:
    args = _ns(no_fail=True, include_potentially=True)
    assert compute_exit_code([_reachable_result(), _potential_result()], args) == (ExitCode.SUCCESS)


# ------------------------------------------------------------------
# Manifest / DB steps
# ------------------------------------------------------------------


def test_parse_manifest_missing_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="[Mm]anifest"):
        parse_manifest(None, tmp_path)


def test_parse_manifest_unsupported_name(tmp_path: Path) -> None:
    manifest = tmp_path / "deps.txt"
    manifest.write_text("requests==2.31.0\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="[Uu]nsupported manifest"):
        parse_manifest("deps.txt", tmp_path)


def test_parse_manifest_requirements(tmp_path: Path) -> None:
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("vuln-lib==1.0.0\n", encoding="utf-8")
    deps = parse_manifest(None, tmp_path)
    assert [(d.name, d.version) for d in deps] == [("vuln-lib", "1.0.0")]


@pytest.mark.parametrize("absolute", [False, True])
def test_manifest_outside_project_is_rejected(tmp_path: Path, absolute: bool) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "requirements.txt"
    outside.write_text("vuln-lib==1.0.0\n", encoding="utf-8")
    manifest = str(outside) if absolute else "../requirements.txt"
    with pytest.raises(ConfigError, match="outside project"):
        parse_manifest(manifest, project)


def test_load_vulnerabilities_missing_db(tmp_path: Path) -> None:
    with pytest.raises(OSVError, match="sync-osv"):
        load_vulnerabilities(str(tmp_path / "nope.db"), [])


def test_sync_cli_imports_local_osv_zip(tmp_path: Path) -> None:
    source = tmp_path / "osv.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            "GHSA-ZIP.json",
            json.dumps(
                {
                    "id": "GHSA-ZIP",
                    "affected": [
                        {
                            "package": {"ecosystem": "PyPI", "name": "vuln-lib"},
                            "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}],
                        }
                    ],
                }
            ),
        )
    db = tmp_path / "osv.db"
    assert main(["sync-osv", "--source", str(source), "--db-path", str(db)]) == 0
    vulns, _ = load_vulnerabilities(
        str(db), [Dependency(name="vuln-lib", version="1.0.0", source="requirements.txt")]
    )
    assert [v.osv_id for v in vulns] == ["GHSA-ZIP"]


def test_load_vulnerabilities_matches_seed(tmp_path: Path) -> None:
    from pyreach.parsers.manifest import Dependency

    db = tmp_path / "osv.db"
    _seed_db(db)
    vulns, versions = load_vulnerabilities(
        str(db), [Dependency(name="vuln-lib", version="1.0.0", source="requirements.txt")]
    )
    assert len(vulns) == 1
    assert vulns[0].cve_id == "CVE-2026-00001"
    assert versions == {"vuln-lib": "1.0.0"}


# ------------------------------------------------------------------
# Formatters
# ------------------------------------------------------------------


def test_format_text_summary_and_paths(tmp_path: Path) -> None:
    graph = nx.DiGraph()
    graph.add_node(
        "vuln_lib.risky",
        file_path=str(tmp_path / "vuln_lib" / "__init__.py"),
        line_number=1,
        node_type="FUNCTION",
    )
    report = format_text(
        tmp_path, ["main.main"], 5, [_reachable_result()], graph, {"vuln-lib": "1.0.0"}
    )
    assert "REACHABLE:              1" in report
    assert "CVE-2026-00001" in report
    assert "main.main -> client.fetch -> vuln_lib.risky" in report
    assert "vuln_lib/__init__.py:1" in report


def test_build_json_document_summary(tmp_path: Path) -> None:
    keyed = {("GHSA-SYNTH-0001", "vuln-lib", "vuln_lib.risky"): _reachable_result()}
    doc = build_json_document(tmp_path, keyed, nx.DiGraph(), {"vuln-lib": "1.0.0"})
    assert doc["tool"] == "PyReach"
    assert doc["summary"] == {
        "total": 1,
        "reachable": 1,
        "potentially_reachable": 0,
        "not_reachable": 0,
    }
    assert doc["results"][0]["status"] == "REACHABLE"
    assert doc["results"][0]["path"] == ["main.main", "client.fetch", "vuln_lib.risky"]


# ------------------------------------------------------------------
# run_scan / main
# ------------------------------------------------------------------


def test_parse_manifest_pipfile_fallback(tmp_path: Path) -> None:
    lock = tmp_path / "Pipfile.lock"
    lock.write_text(json.dumps({"default": {"vuln-lib": {"version": "==1.0.0"}}}), encoding="utf-8")
    deps = parse_manifest(None, tmp_path)
    assert [(d.name, d.version) for d in deps] == [("vuln-lib", "1.0.0")]


def test_load_vulnerabilities_corrupt_db(tmp_path: Path) -> None:
    bad = tmp_path / "osv.db"
    bad.write_text("not a database", encoding="utf-8")
    from pyreach.parsers.manifest import Dependency

    with pytest.raises(OSVError, match="corrupt"):
        load_vulnerabilities(
            str(bad), [Dependency(name="vuln-lib", version="1.0.0", source="requirements.txt")]
        )


def test_load_library_modules_from_installed_package(tmp_path: Path) -> None:
    import pyreach.cli as cli_mod
    from pyreach.loaders.packages import InstalledPackage
    from pyreach.osv.mapper import Vulnerability

    lib_dir = tmp_path / "site-packages" / "vuln_lib"
    lib_dir.mkdir(parents=True)
    (lib_dir / "__init__.py").write_text("def risky():\n    return 1\n", encoding="utf-8")
    pkg = InstalledPackage(
        name="vuln-lib",
        version="1.0.0",
        location=tmp_path / "site-packages",
        top_level=["vuln_lib"],
    )
    vuln = Vulnerability(
        osv_id="GHSA-SYNTH-0001",
        cve_id=None,
        package_name="vuln-lib",
        severity_score=None,
        severity_level=None,
        summary="s",
        affected_symbols=["vuln_lib.risky"],
        version_introduced=None,
        version_fixed=None,
    )

    class _FakeResolver:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def resolve(self, name: str) -> InstalledPackage | None:
            assert name == "vuln-lib"
            return pkg

    modules = cli_mod.load_library_modules([vuln], _FakeResolver())
    assert [m.module_fqn for m in modules] == ["vuln_lib"]


def test_run_scan_negative_max_depth(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="max_depth"):
        run_scan(_ns(project_path=str(tmp_path), max_depth=-1))


def test_run_scan_missing_project() -> None:
    with pytest.raises(ConfigError, match="PROJECT_PATH"):
        run_scan(_ns(project_path=None))


def test_run_scan_no_vulns_short_circuits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "requirements.txt").write_text("clean-lib==1.0.0\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    db = tmp_path / "osv.db"
    _seed_db(db)
    monkeypatch.chdir(tmp_path)
    code = run_scan(_ns(project_path=str(tmp_path), db_path=str(db), format="sarif"))
    assert code == ExitCode.SUCCESS
    out = json.loads((tmp_path / "pyreach-results.sarif").read_text(encoding="utf-8"))
    assert out["runs"][0]["results"] == []


def test_run_scan_full_pipeline_sarif(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "projects" / "linear_reachable"
    db = tmp_path / "osv.db"
    _seed_db(db)
    monkeypatch.chdir(tmp_path)
    code = run_scan(
        _ns(project_path=str(fixture), db_path=str(db), format="sarif", entry_point=["main.main"])
    )
    assert code == ExitCode.FINDINGS
    doc = json.loads((tmp_path / "pyreach-results.sarif").read_text(encoding="utf-8"))
    assert doc["runs"][0]["results"][0]["ruleId"] == "PYREACH-REACHABLE-CVE"


def test_run_scan_full_pipeline_text_no_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "projects" / "linear_reachable"
    db = tmp_path / "osv.db"
    _seed_db(db)
    monkeypatch.chdir(tmp_path)
    code = run_scan(
        _ns(
            project_path=str(fixture),
            db_path=str(db),
            format="text",
            entry_point=["main.main"],
            no_fail=True,
        )
    )
    assert code == ExitCode.SUCCESS
    out = capsys.readouterr().out
    assert "REACHABLE:              1" in out
    assert "main.main -> client.fetch -> vuln_lib.risky" in out


def test_main_missing_project_returns_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["/definitely/not/here"]) == 2
    assert "Error" in capsys.readouterr().err


def test_main_keyboard_interrupt_returns_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def _interrupted(*args: object) -> int:
        raise KeyboardInterrupt()

    monkeypatch.setattr("pyreach.cli.run_scan", _interrupted)
    assert main([str(tmp_path)]) == 2
    assert "interrupted" in capsys.readouterr().err


def test_main_memory_error_returns_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def _boom(*args: object) -> int:
        raise MemoryError()

    monkeypatch.setattr("pyreach.cli.run_scan", _boom)
    assert main([str(tmp_path)]) == 2
    assert "--max-depth" in capsys.readouterr().err


def test_emit_text_writes_file_when_output_given(tmp_path: Path) -> None:
    import pyreach.cli as cli_mod

    out = tmp_path / "report.txt"
    written = cli_mod.emit_output(
        _ns(format="text", output=str(out), max_depth=5),
        tmp_path,
        {},
        nx.DiGraph(),
        {},
        ["main.main"],
    )
    assert written == out
    assert "Entry points: main.main" in out.read_text(encoding="utf-8")


def test_main_unexpected_exception_returns_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "requirements.txt").write_text("a==1\n", encoding="utf-8")
    monkeypatch.setattr("pyreach.cli.parse_manifest", lambda *a: 1 / 0)  # type: ignore[arg-type]
    assert main([str(tmp_path)]) == 2
    assert "Error" in capsys.readouterr().err


def test_explicit_unsupported_manifest_is_not_silently_ignored(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("real-lib==1.0\n", encoding="utf-8")
    (tmp_path / "deps.txt").write_text("wrong-lib==9.9\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="[Uu]nsupported manifest"):
        parse_manifest("deps.txt", tmp_path)


def test_fail_on_reachable_false_gates_out_findings() -> None:
    assert compute_exit_code([_reachable_result()], _ns(fail_on_reachable=False)) == (
        ExitCode.SUCCESS
    )


def test_symbol_module_file_rejects_traversal(tmp_path: Path) -> None:
    from pyreach.loaders.packages import InstalledPackage

    pkg = InstalledPackage(name="pkg", version="1.0", location=tmp_path, top_level=["pkg"])
    assert _symbol_module_file("../../etc", pkg) is None
    assert _symbol_module_file("..", pkg) is None
    assert _symbol_module_file("", pkg) is None
