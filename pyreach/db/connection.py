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
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Database operation failed: {exc}") from exc
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
        version = get_schema_version(conn)
        if version < 1:
            raise DatabaseError("Schema initialization failed to record schema_version.")
