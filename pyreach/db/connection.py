"""Database connection and initialization utilities."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

from pyreach.exceptions import OSVError


class DatabaseError(OSVError):
    """Raised when a SQLite database operation fails."""


@contextmanager
def get_db_connection(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with Row factory and foreign keys enabled.

    Automatically commits on normal exit and rolls back on exception.
    """
    resolved_path = Path(db_path).expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(resolved_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    try:
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise DatabaseError(f"Database operation failed: {exc}") from exc
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version recorded in the database."""
    cursor = conn.execute("SELECT MAX(version) FROM schema_version;")
    row = cursor.fetchone()
    if row and row[0] is not None:
        return int(row[0])
    return 0


def initialize_database(db_path: str | Path) -> None:
    """Create all schema tables and indexes in the target SQLite database."""
    schema_sql = resources.files("pyreach.db").joinpath("schema.sql").read_text(encoding="utf-8")
    with get_db_connection(db_path) as conn:
        conn.executescript(schema_sql)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(affected_symbols);")}
        if "package_name" not in columns:
            conn.execute("ALTER TABLE affected_symbols ADD COLUMN package_name TEXT;")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_affected_symbols_package "
            "ON affected_symbols(package_name);"
        )
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'reachability_results'"
        ).fetchone()
        if row and "BETWEEN 1 AND 5" in row[0]:
            migration = (
                resources.files("pyreach.db")
                .joinpath("migrations/002_depth_domain.sql")
                .read_text(encoding="utf-8")
            )
            conn.executescript(migration)
        conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (2);")
        version = get_schema_version(conn)
        if version < 1:
            raise DatabaseError("Schema initialization failed to record schema_version.")
