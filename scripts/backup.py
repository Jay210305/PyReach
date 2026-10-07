"""Offline backup utility for PyReach SQLite database.

Uses SQLite Online Backup API (sqlite3.Connection.backup) which is
crash-safe under WAL mode. Intended for manual or cron invocation;
no retention policy is enforced here — retention is a deployment
concern (copy the file off-runner).
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup_db(source: Path, dest_dir: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source DB not found: {source}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = dest_dir / f"osv-{ts}.db"
    src_conn = sqlite3.connect(str(source))
    try:
        # Ensure WAL checkpoint before backup for consistency
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        dst_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup PyReach OSV SQLite DB (WAL-safe)")
    parser.add_argument("--db-path", default="~/.pyreach/osv.db", help="Source DB path")
    parser.add_argument("--dest-dir", default="~/.pyreach/backups", help="Destination directory")
    args = parser.parse_args()
    dest = backup_db(Path(args.db_path), Path(args.dest_dir))
    print(f"Backup created: {dest}")


if __name__ == "__main__":
    main()
