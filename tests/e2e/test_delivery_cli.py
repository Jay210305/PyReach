"""Public CLI contract, real subprocesses and offline data."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.integration.test_delivery_regressions import record

ROOT = Path(__file__).resolve().parents[2]


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pyreach", *map(str, args)], capture_output=True, text=True, cwd=ROOT
    )


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "app"
    p.mkdir()
    (p / "requirements.txt").write_text("vuln-lib==1.5\n")
    (p / "main.py").write_text(
        "import vuln_lib\ndef main():\n    vuln_lib.risky()\n"
        "if __name__ == '__main__':\n    main()\n"
    )
    source = tmp_path / "osv.jsonl"
    source.write_text(json.dumps(record()) + "\n")
    db = tmp_path / "osv.db"
    c = cli("sync-osv", "--source", source, "-d", db)
    assert c.returncode == 0, c.stderr
    return p, db


@pytest.mark.parametrize("option", ["--help", "--version"])
def test_information_without_project(option):
    assert cli(option).returncode == 0


@pytest.mark.parametrize("fmt", ["sarif", "json", "text"])
def test_scan_reports_and_exit_policy(project, tmp_path, fmt):
    p, db = project
    output = tmp_path / f"report.{fmt}"
    c = cli(p, "-d", db, "-o", output, "-f", fmt)
    assert c.returncode == 1, c.stderr
    assert output.is_file()
    if fmt == "sarif":
        import jsonschema

        schema = json.loads((ROOT / "tests/fixtures/sarif-schema-2.1.0.json").read_text())
        doc = json.loads(output.read_text())
        jsonschema.validate(doc, schema)
        assert doc["runs"][0]["results"][0]["ruleId"] == "PYREACH-REACHABLE-CVE"
    elif fmt == "json":
        assert json.loads(output.read_text())["results"][0]["status"] == "REACHABLE"
    assert cli(p, "-d", db, "-o", output, "--no-fail").returncode == 0


@pytest.mark.parametrize("depth", ["-1", "8", "wrong"])
def test_invalid_depth_returns_two(project, depth):
    p, db = project
    assert cli(p, "-d", db, "-k", depth).returncode == 2


def test_missing_database_returns_two(project, tmp_path):
    p, _ = project
    c = cli(p, "-d", tmp_path / "absent.db")
    assert c.returncode == 2 and "sync-osv" in c.stderr


def test_manifest_cannot_escape_root(project, tmp_path):
    p, db = project
    (tmp_path / "outside.txt").write_text("vuln-lib==1.5\n")
    assert cli(p, "-d", db, "-m", "../outside.txt").returncode == 2


def test_configuration_precedence_and_unknown_keys(project, tmp_path):
    p, db = project
    (p / ".pyreach.yml").write_text(
        "pyreach:\n  max_depth: 0\n  thresholds:\n    fail_on_potentially: true\n"
    )
    out = tmp_path / "out.json"
    assert cli(p, "-d", db, "-f", "json", "-o", out, "-k", "5").returncode == 1
    (p / ".pyreach.yml").write_text("pyreach:\n  misspelled: true\n")
    assert cli(p, "-d", db).returncode == 2


def test_partial_source_remains_potential(project, tmp_path):
    p, db = project
    (p / "bad.py").write_bytes(b"\xff")
    out = tmp_path / "out.json"
    c = cli(p, "-d", db, "-f", "json", "-o", out)
    assert c.returncode == 1
    assert json.loads(out.read_text())["diagnostics"]


def test_top_level_script_is_analyzed_without_execution(project, tmp_path):
    p, db = project
    sentinel = tmp_path / "must-not-exist"
    (p / "main.py").write_text(
        "import vuln_lib\nfrom pathlib import Path\n"
        f"Path({str(sentinel)!r}).touch()\nvuln_lib.risky()\n"
    )
    assert cli(p, "-d", db, "--no-cache").returncode == 1
    assert not sentinel.exists()


def test_explicit_entry_point_is_resolved_and_unknown_is_rejected(project):
    p, db = project
    assert cli(p, "-d", db, "-e", "main:main").returncode == 1
    assert cli(p, "-d", db, "-e", "missing:func").returncode == 2


def test_installed_transitives_and_external_library_sources(project, tmp_path):
    p, db = project
    (p / "requirements.txt").write_text("demo>=0.5\n")
    site = p / ".venv/lib/python3.10/site-packages"
    site.mkdir(parents=True)
    for name, version, requires in [
        ("demo", "1.0", "Requires-Dist: vuln-lib>=1\n"),
        ("vuln_lib", "1.5", ""),
    ]:
        metadata = site / f"{name}-{version}.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n{requires}"
        )
        (metadata / "top_level.txt").write_text(name + "\n")
        package = site / name
        package.mkdir()
        (package / "__init__.py").write_text("def risky():\n    pass\n")
    output = tmp_path / "transitive.json"
    c = cli(p, "-d", db, "-o", output, "-f", "json", "--no-cache")
    assert c.returncode == 1, c.stderr
    doc = json.loads(output.read_text())
    assert doc["results"][0]["vulnerability"]["package_name"] == "vuln-lib"
    assert doc["results"][0]["status"] == "REACHABLE"
