"""Replica scan benchmark guarding the <45s CI budget (S4-T7).

Scans a copy of the real PyReach package tree (mid-size, ~30 modules) with
a seeded advisory DB. Marked `performance`: excluded from default runs.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
import tracemalloc
from pathlib import Path

import pytest

from pyreach.cli import main
from pyreach.db.connection import initialize_database

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_BUDGET_S = 45.0
SARIF_BUDGET_BYTES = 5 * 1024 * 1024


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _seed_db(db_path: Path) -> None:
    initialize_database(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute(
            "INSERT INTO advisories (osv_id, cve_id, package_name, ecosystem,"
            " severity_score, severity_level, summary)"
            " VALUES ('GHSA-BENCH-0001','CVE-2024-00001','networkx','PyPI',7.5,"
            " 'HIGH','benchmark')"
        )
        conn.execute(
            "INSERT INTO affected_symbols (advisory_id, symbol_fqn)"
            " VALUES (?, 'networkx.DiGraph.successors')",
            (cur.lastrowid,),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.mark.performance
def test_mid_size_tree_scan_within_budget(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "mid"
    shutil.copytree(
        REPO_ROOT / "pyreach",
        project / "pyreach",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (project / "requirements.txt").write_text("networkx==3.4.2\n", encoding="utf-8")
    db = tmp_path / "osv.db"
    _seed_db(db)
    out = tmp_path / "bench.sarif"

    tracemalloc.start()
    start = time.perf_counter()
    code = main([str(project), "-d", str(db), "-o", str(out), "-q"])
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    capsys.readouterr()

    assert code in (0, 1)
    assert elapsed < SCAN_BUDGET_S, f"scan took {elapsed:.2f}s"
    assert peak < 2 * 1024 * 1024 * 1024
    assert out.exists()
    assert out.stat().st_size < SARIF_BUDGET_BYTES
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["version"] == "2.1.0"
