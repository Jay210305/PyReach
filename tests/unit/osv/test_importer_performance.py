import json
from pathlib import Path

import pytest

from pyreach.db.connection import get_db_connection, initialize_database
from pyreach.osv.importer import OSVImporter

RECORD_COUNT = 10_000


@pytest.mark.performance
def test_import_10k_records(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)

    jsonl = tmp_path / "bulk.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for i in range(RECORD_COUNT):
            record = {
                "id": f"GHSA-{i:04d}",
                "summary": "bulk record",
                "modified": f"2024-01-{i % 28 + 1:02d}T00:00:00Z",
                "affected": [
                    {
                        "package": {"name": f"pkg-{i}", "ecosystem": "PyPI"},
                        "ranges": [
                            {
                                "type": "ECOSYSTEM",
                                "events": [{"introduced": "0"}, {"fixed": "2.0.0"}],
                            }
                        ],
                    }
                ],
            }
            f.write(json.dumps(record) + "\n")

    stats = OSVImporter(db_path).import_file(jsonl)

    assert stats.imported == RECORD_COUNT
    assert stats.elapsed_seconds < 300  # S1-T5 acceptance: < 5 min

    with get_db_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM advisories;").fetchone()[0]
        assert count == RECORD_COUNT
