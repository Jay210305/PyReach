from pathlib import Path

import pytest

from pyreach.db.connection import get_db_connection, initialize_database
from pyreach.db.repositories import AdvisoryRepository
from pyreach.exceptions import OSVError
from pyreach.osv.importer import OSVImporter, sync_osv

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "osv_records"


def test_import_single_record(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)

    sample_jsonl = FIXTURES_DIR / "sample.jsonl"
    importer = OSVImporter(db_path)
    stats = importer.import_file(sample_jsonl)

    assert stats.imported == 3  # requests, flask, urllib3
    assert stats.skipped_ecosystem == 1  # npm lodash
    assert stats.skipped_malformed == 1  # {not valid json line}
    assert stats.symbols_imported >= 3  # requests has 2 symbols, flask gets *, urllib3 gets *

    with get_db_connection(db_path) as conn:
        advisories_count = conn.execute("SELECT COUNT(*) FROM advisories;").fetchone()[0]
        assert advisories_count == 3

        # Check requests advisory
        row = conn.execute("SELECT * FROM advisories WHERE package_name = 'requests';").fetchone()
        assert row is not None
        assert row["cve_id"] == "CVE-2023-32681"
        assert row["severity_level"] == "HIGH"


def test_idempotent_reimport(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)
    sample_jsonl = FIXTURES_DIR / "sample.jsonl"

    importer = OSVImporter(db_path)
    importer.import_file(sample_jsonl)
    importer.import_file(sample_jsonl)

    with get_db_connection(db_path) as conn:
        advisories_count = conn.execute("SELECT COUNT(*) FROM advisories;").fetchone()[0]
        assert advisories_count == 3


def test_incremental_skips_old(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)
    sample_jsonl = FIXTURES_DIR / "sample.jsonl"

    importer = OSVImporter(db_path, incremental=True)
    first_stats = importer.import_file(sample_jsonl)
    assert first_stats.imported == 3

    # Second run with incremental skips all already modified records
    second_stats = importer.import_file(sample_jsonl)
    assert second_stats.imported == 0


def test_sync_osv_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    jsonl_dir = tmp_path / "dumps"
    jsonl_dir.mkdir()

    f1 = jsonl_dir / "dump1.jsonl"
    f1.write_text(
        '{"id":"GHSA-0001","affected":[{"package":{"name":"flask","ecosystem":"PyPI"}}]}\n',
        encoding="utf-8",
    )
    f2 = jsonl_dir / "dump2.jsonl"
    f2.write_text(
        '{"id":"GHSA-0002","affected":[{"package":{"name":"click","ecosystem":"PyPI"}}]}\n',
        encoding="utf-8",
    )

    stats = sync_osv(db_path, jsonl_dir)
    assert stats.imported == 2

    with get_db_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM advisories;").fetchone()[0]
        assert count == 2


def test_sync_osv_rejects_url(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    with pytest.raises(OSVError) as exc_info:
        sync_osv(db_path, "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip")
    assert "Network download is not supported" in str(exc_info.value)


def test_find_by_package_and_version(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    initialize_database(db_path)
    sample_jsonl = FIXTURES_DIR / "sample.jsonl"

    importer = OSVImporter(db_path)
    importer.import_file(sample_jsonl)

    with get_db_connection(db_path) as conn:
        repo = AdvisoryRepository(conn)
        # requests 2.30.0 is affected by CVE-2023-32681 ([2.0.0, 2.31.0))
        vulns_affected = repo.find_by_package_and_version("requests", "2.30.0")
        assert len(vulns_affected) == 1
        assert vulns_affected[0].cve_id == "CVE-2023-32681"

        # requests 2.31.0 is fixed
        vulns_fixed = repo.find_by_package_and_version("requests", "2.31.0")
        assert len(vulns_fixed) == 0


def test_import_empty_file(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("", encoding="utf-8")

    importer = OSVImporter(db_path)
    stats = importer.import_file(empty_file)
    assert stats.total == 0
    assert stats.imported == 0
    assert stats.skipped_ecosystem == 0
    assert stats.skipped_malformed == 0


def test_import_file_not_found(tmp_path: Path) -> None:
    db_path = tmp_path / "osv.db"
    missing = tmp_path / "missing.jsonl"

    importer = OSVImporter(db_path)
    with pytest.raises(OSVError) as exc_info:
        importer.import_file(missing)
    assert "not found" in str(exc_info.value)


def test_conftest_osv_fixtures(
    sample_osv_jsonl: Path,
    sqlite_db: tuple[Path, object],
) -> None:
    db_path, conn_factory = sqlite_db
    importer = OSVImporter(db_path)
    stats = importer.import_file(sample_osv_jsonl)
    assert stats.total == 5
    assert stats.imported == 3
    assert stats.skipped_ecosystem == 1
    assert stats.skipped_malformed == 1
