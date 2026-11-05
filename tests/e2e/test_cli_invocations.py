"""E2E CLI invocations via subprocess (S4-T3).

Asserts real process exit codes and artifacts on the S3-T8 synthetic
projects. A seeded SQLite DB (stub advisory) keeps everything offline.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from pyreach import __version__
from pyreach.db.connection import initialize_database

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT / "tests" / "fixtures" / "projects"


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


@pytest.fixture()
def project_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "linear_reachable"
    shutil.copytree(PROJECTS_DIR / "linear_reachable", dst)
    return dst


@pytest.fixture()
def seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "osv.db"
    _seed_db(db)
    return db


def _run(*argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # Isolate the user-global ~/.pyreach/config.yml so e2e stays hermetic.
    env["HOME"] = str(cwd)
    env["USERPROFILE"] = str(cwd)
    return subprocess.run(
        [sys.executable, "-m", "pyreach.cli", *argv],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_help(tmp_path: Path) -> None:
    proc = _run("--help", cwd=tmp_path)
    assert proc.returncode == 0
    for option in (
        "--manifest",
        "--db-path",
        "--output",
        "--entry-point",
        "--max-depth",
        "--include-potentially",
        "--include-all",
        "--no-fail",
        "--format",
        "--exclude",
        "--cache",
        "--quiet",
        "--verbose",
        "--version",
    ):
        assert option in proc.stdout


def test_cli_version(tmp_path: Path) -> None:
    proc = _run("--version", cwd=tmp_path)
    assert proc.returncode == 0
    assert f"PyReach {__version__}" in proc.stdout


def test_cli_missing_project(tmp_path: Path) -> None:
    proc = _run(str(tmp_path / "nope"), cwd=tmp_path)
    assert proc.returncode == 2


def test_cli_missing_manifest(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = _run(str(empty), cwd=tmp_path)
    assert proc.returncode == 2
    assert "anifest" in proc.stderr


def test_cli_missing_db(tmp_path: Path, project_copy: Path) -> None:
    proc = _run(str(project_copy), "-d", str(tmp_path / "nope.db"), cwd=tmp_path)
    assert proc.returncode == 2
    assert "sync-osv" in proc.stderr


def test_cli_text_format(tmp_path: Path, project_copy: Path, seeded_db: Path) -> None:
    proc = _run(
        str(project_copy),
        "-f",
        "text",
        "-e",
        "main.main",
        "-d",
        str(seeded_db),
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert "REACHABLE:              1" in proc.stdout
    assert "CVE-2026-00001" in proc.stdout


def test_cli_output_file(tmp_path: Path, project_copy: Path, seeded_db: Path) -> None:
    out = tmp_path / "out.sarif"
    proc = _run(
        str(project_copy),
        "-e",
        "main.main",
        "-d",
        str(seeded_db),
        "-o",
        str(out),
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert out.exists()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["results"][0]["ruleId"] == "PYREACH-REACHABLE-CVE"


def test_cli_config_fail_on_potentially(tmp_path: Path, seeded_db: Path) -> None:
    dst = tmp_path / "dynamic_import"
    shutil.copytree(PROJECTS_DIR / "dynamic_import", dst)
    base = [str(dst), "-f", "text", "-e", "main.main", "-d", str(seeded_db)]
    without_config = _run(*base, cwd=tmp_path)
    assert without_config.returncode == 0
    assert "POTENTIALLY REACHABLE:  1" in without_config.stdout
    (dst / ".pyreach.yml").write_text(
        "pyreach:\n  thresholds:\n    fail_on_potentially: true\n", encoding="utf-8"
    )
    with_config = _run(*base, cwd=tmp_path)
    assert with_config.returncode == 1
    assert "POTENTIALLY REACHABLE:  1" in with_config.stdout


def test_cli_quiet_suppresses_progress(tmp_path: Path, project_copy: Path, seeded_db: Path) -> None:
    proc = _run(
        str(project_copy),
        "-f",
        "text",
        "-e",
        "main.main",
        "-d",
        str(seeded_db),
        "-q",
        cwd=tmp_path,
    )
    assert proc.returncode == 1
    assert "[1/" not in proc.stderr
