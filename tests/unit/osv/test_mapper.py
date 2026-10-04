import json
from pathlib import Path

from pyreach.db.connection import get_db_connection, initialize_database
from pyreach.osv.importer import OSVImporter
from pyreach.osv.mapper import VulnerabilityMapper


def _import_records(tmp_path: Path, records: list[dict]) -> Path:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)
    jsonl = tmp_path / "records.jsonl"

    jsonl.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    OSVImporter(db_path).import_file(jsonl)
    return db_path


def test_last_affected_boundary_inclusive(tmp_path: Path) -> None:
    db_path = _import_records(
        tmp_path,
        [
            {
                "id": "GHSA-LAST",
                "affected": [
                    {
                        "package": {"name": "cryptography", "ecosystem": "PyPI"},
                        "ranges": [
                            {
                                "type": "ECOSYSTEM",
                                "events": [
                                    {"introduced": "3.0.0"},
                                    {"last_affected": "3.4.7"},
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    )
    with get_db_connection(db_path) as conn:
        mapper = VulnerabilityMapper(conn)
        assert len(mapper.find_by_package_and_version("cryptography", "3.4.7")) == 1
        assert len(mapper.find_by_package_and_version("cryptography", "3.4.8")) == 0


def test_multi_range_lookup(tmp_path: Path) -> None:
    db_path = _import_records(
        tmp_path,
        [
            {
                "id": "GHSA-MULTI",
                "affected": [
                    {
                        "package": {"name": "pkg", "ecosystem": "PyPI"},
                        "ranges": [
                            {
                                "type": "ECOSYSTEM",
                                "events": [
                                    {"introduced": "1.0.0"},
                                    {"fixed": "1.5.0"},
                                    {"introduced": "2.0.0"},
                                    {"fixed": "2.1.0"},
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    )
    with get_db_connection(db_path) as conn:
        mapper = VulnerabilityMapper(conn)
        assert len(mapper.find_by_package_and_version("pkg", "1.2.0")) == 1
        assert len(mapper.find_by_package_and_version("pkg", "1.7.0")) == 0
        assert len(mapper.find_by_package_and_version("pkg", "2.0.5")) == 1