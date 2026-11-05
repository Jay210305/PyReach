"""Validation for CI/CD stage templates and gate behavior (S4-T6)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
import yaml

from pyreach.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
CI_ROOT = REPO_ROOT / "ci"
PROJECTS_DIR = REPO_ROOT / "tests" / "fixtures" / "projects"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _seed_db(db_path: Path) -> None:
    from pyreach.db.connection import initialize_database

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


def test_gitlab_template_parses() -> None:
    doc = yaml.safe_load((CI_ROOT / "gitlab" / ".pyreach-scan.yml").read_text())
    assert isinstance(doc, dict)
    assert ".pyreach-scan" in doc


def test_gitlab_template_gate_structure() -> None:
    doc = yaml.safe_load((CI_ROOT / "gitlab" / ".pyreach-scan.yml").read_text())
    job = doc[".pyreach-scan"]
    assert job["stage"] == "security"
    assert job["allow_failure"] is False
    assert set(("lidercom-local-runner", "security")) <= set(job["tags"])
    assert job["artifacts"]["reports"]["sarif"] == "$PYREACH_OUTPUT"
    assert job["image"] == {"name": "pyreach:0.1.0", "entrypoint": [""]}
    script = "\n".join(job["script"])
    for flag in ("--format sarif", "--include-potentially", "--db-path", "--output"):
        assert flag in script
    assert "PYREACH_SCAN_OVERRIDE" in script
    assert 'pyreach "$PYREACH_PROJECT_PATH" \\' in script
    assert "printf '%s\\n' \"$scan_exit\" > pyreach-exit-code.txt" in script
    assert job["artifacts"]["when"] == "always"
    gate = doc[".pyreach-gate"]
    assert gate["needs"][0]["job"] == "pyreach_scan"
    assert "pyreach-exit-code.txt" in "\n".join(gate["script"])


def test_example_includes_template_and_extends() -> None:
    doc = yaml.safe_load((CI_ROOT / "examples" / ".gitlab-ci.yml").read_text())
    assert {"local": "ci/gitlab/.pyreach-scan.yml"} in doc["include"]
    assert doc["pyreach_scan"]["extends"] == ".pyreach-scan"


def test_jenkinsfile_structure() -> None:
    text = (CI_ROOT / "jenkins" / "Jenkinsfile.pyreach").read_text()
    assert "label 'lidercom-local-runner'" in text
    assert "Security Scan" in text
    assert "archiveArtifacts" in text
    assert "recordIssues" in text and "sarif" in text
    assert "OSV database missing" in text
    assert text.count("{") == text.count("}")


def test_sync_script_posix() -> None:
    text = (CI_ROOT / "scripts" / "sync-pyreach-osv.sh").read_text()
    assert text.startswith("#!/bin/sh")
    assert "[[" not in text
    assert "function " not in text
    assert "sync-osv" in text
    assert '--source "$PYREACH_OSV_SOURCE"' in text
    assert 'PYREACH_OSV_SOURCE="${PYREACH_OSV_SOURCE:-}"' in text


def test_sync_script_syntax() -> None:
    sh = shutil.which("sh")
    if sh is None:
        pytest.skip("POSIX sh not available on this platform")
    proc = subprocess.run(
        [sh, "-n", str(CI_ROOT / "scripts" / "sync-pyreach-osv.sh")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr


def test_dockerfile_structure() -> None:
    text = (CI_ROOT / "docker" / "Dockerfile.pyreach").read_text()
    assert "FROM python:3.10-slim" in text
    assert 'ENTRYPOINT ["pyreach"]' in text
    assert "osv.db" in text
    assert "/tmp/pyreach-0.1.0-py3-none-any.whl" in text
    assert "/tmp/pyreach.whl" not in text


def _copy_project(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / name
    shutil.copytree(PROJECTS_DIR / name, dst)
    return dst


def test_gate_blocks_on_reachable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _copy_project("linear_reachable", tmp_path)
    db = tmp_path / "osv.db"
    _seed_db(db)
    out = tmp_path / "gate.sarif"
    monkeypatch.chdir(tmp_path)
    code = main([str(project), "-e", "main.main", "-d", str(db), "-o", str(out), "-q"])
    assert code == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    levels = [r["level"] for r in doc["runs"][0]["results"]]
    assert "error" in levels


def test_gate_passes_on_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _copy_project("package_unused", tmp_path)
    db = tmp_path / "osv.db"
    _seed_db(db)
    out = tmp_path / "gate.sarif"
    monkeypatch.chdir(tmp_path)
    code = main([str(project), "-e", "main.main", "-d", str(db), "-o", str(out), "-q"])
    assert code == 0
