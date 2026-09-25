from pathlib import Path

import pytest

from pyreach.db.connection import (
    DatabaseError,
    get_db_connection,
    get_schema_version,
    initialize_database,
)

EXPECTED_TABLES = {
    "advisories",
    "affected_symbols",
    "cg_nodes",
    "cg_edges",
    "reachability_results",
    "file_hashes",
    "schema_version",
}

EXPECTED_INDEXES = {
    "idx_advisories_package",
    "idx_advisories_cve",
    "idx_advisories_severity",
    "idx_advisories_modified",
    "idx_affected_symbols_advisory",
    "idx_affected_symbols_fqn",
    "idx_cg_nodes_fqn",
    "idx_cg_nodes_file",
    "idx_cg_edges_caller",
    "idx_cg_edges_callee",
    "idx_reachability_symbol",
    "idx_reachability_entry",
}


def test_initialize_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        assert EXPECTED_TABLES.issubset(tables)


def test_foreign_keys_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        cursor = conn.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1


def test_unique_osv_id(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO advisories (osv_id, package_name) VALUES ('GHSA-1234', 'requests');"
        )

    with pytest.raises(DatabaseError) as exc_info:
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO advisories (osv_id, package_name) VALUES ('GHSA-1234', 'requests');"
            )
    assert "UNIQUE constraint failed" in str(exc_info.value)


def test_cascade_delete(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO advisories (osv_id, package_name) VALUES ('GHSA-1234', 'requests');"
        )
        advisory_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO affected_symbols (advisory_id, symbol_fqn) VALUES (?, ?);",
            (advisory_id, "requests.get"),
        )

    with get_db_connection(db_path) as conn:
        sym_count = conn.execute("SELECT COUNT(*) FROM affected_symbols;").fetchone()[0]
        assert sym_count == 1
        conn.execute("DELETE FROM advisories WHERE id = ?;", (advisory_id,))

    with get_db_connection(db_path) as conn:
        sym_count = conn.execute("SELECT COUNT(*) FROM affected_symbols;").fetchone()[0]
        assert sym_count == 0


def test_indexes_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = {row["name"] for row in cursor.fetchall()}
        assert EXPECTED_INDEXES.issubset(indexes)


def test_schema_version_is_one(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        version = get_schema_version(conn)
        assert version == 1


def test_connection_rollback_on_error(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)

    with pytest.raises(DatabaseError):
        with get_db_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO advisories (osv_id, package_name) VALUES ('GHSA-ROLLBACK', 'flask');"
            )
            # Cause an error
            conn.execute("INSERT INTO non_existent_table VALUES (1);")

    with get_db_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM advisories WHERE osv_id = 'GHSA-ROLLBACK';").fetchone()
        assert row is None


def test_initialize_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    initialize_database(db_path)
    initialize_database(db_path)

    with get_db_connection(db_path) as conn:
        assert get_schema_version(conn) == 1


def test_parent_directory_created(tmp_path: Path) -> None:
    db_path = tmp_path / "deep" / "nested" / "dir" / "osv.db"
    assert not db_path.parent.exists()
    initialize_database(db_path)
    assert db_path.exists()
