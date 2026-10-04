"""OSV JSON streaming importer and synchronization."""

import json
import sqlite3
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from pyreach.db.connection import get_db_connection, initialize_database
from pyreach.db.repositories import AdvisoryRepository
from pyreach.exceptions import OSVError
from pyreach.parsers.osv_json import extract_affected, is_pypi_record, parse_osv_record

_NETWORK_SCHEMES = ("http://", "https://", "ftp://")
_BATCH_SIZE = 1000
_LAST_SYNC_KEY = "last_sync"


@dataclass
class ImportStats:
    """Statistics collected during an OSV import run."""

    total: int = 0
    imported: int = 0
    skipped_ecosystem: int = 0
    skipped_malformed: int = 0
    skipped_up_to_date: int = 0
    symbols_imported: int = 0
    elapsed_seconds: float = 0.0


def iter_osv_records(path: Path) -> Iterator[dict[str, Any] | None]:
    """Yield record dicts from a JSONL file or a top-level JSON array file.

    Malformed records are yielded as ``None`` so the caller can count them
    without aborting the stream. JSON arrays are loaded whole (they are small
    compared to the JSONL bulk dumps).
    """
    with path.open("r", encoding="utf-8", errors="replace") as f:
        first = f.read(1)
        while first and first.isspace():
            first = f.read(1)
        f.seek(0)
        if first == "[":
            yield from _iter_array_records(f)
            return
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                yield None
                continue
            yield record if isinstance(record, dict) else None


def _iter_array_records(f: TextIO) -> Iterator[dict[str, Any] | None]:
    try:
        data = json.load(f)
    except json.JSONDecodeError:
        yield None
        return
    if not isinstance(data, list):
        yield None
        return
    for item in data:
        yield item if isinstance(item, dict) else None


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _date_part(value: Any) -> str | None:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def _read_last_sync(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT value FROM sync_metadata WHERE key = ?;", (_LAST_SYNC_KEY,)
    ).fetchone()
    return row[0] if row else None


def _write_last_sync(conn: sqlite3.Connection, value: str) -> None:
    conn.execute(
        "INSERT INTO sync_metadata (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
        (_LAST_SYNC_KEY, value),
    )


class OSVImporter:
    """Bulk importer for OSV vulnerability data into SQLite."""

    def __init__(self, db_path: str | Path, incremental: bool = False) -> None:
        self.db_path = Path(db_path)
        self.incremental = incremental

    def import_file(self, path: str | Path) -> ImportStats:
        """Stream an OSV JSONL (or JSON array) file and insert/update advisories."""
        file_path = Path(path)
        if not file_path.is_file():
            raise OSVError(f"OSV data file not found: {file_path}")

        stats = ImportStats()
        start_time = time.monotonic()

        initialize_database(self.db_path)
        with get_db_connection(self.db_path) as conn:
            repo = AdvisoryRepository(conn)
            last_sync = _read_last_sync(conn) if self.incremental else None
            sync_start = _utc_timestamp() if self.incremental else None

            for record in iter_osv_records(file_path):
                stats.total += 1
                if record is None:
                    stats.skipped_malformed += 1
                    continue

                modified = record.get("modified")
                if (
                    self.incremental
                    and last_sync
                    and isinstance(modified, str)
                    and modified <= last_sync
                ):
                    stats.skipped_up_to_date += 1
                    continue

                if not is_pypi_record(record):
                    stats.skipped_ecosystem += 1
                    continue

                vuln = parse_osv_record(record)
                if vuln is None:
                    stats.skipped_malformed += 1
                    continue

                aliases = record.get("aliases")
                advisory_id = repo.upsert(
                    advisory=vuln,
                    modified_date=modified if isinstance(modified, str) else None,
                    published_date=_date_part(record.get("published")),
                    aliases=aliases if isinstance(aliases, list) else None,
                    raw_json=json.dumps(record, ensure_ascii=False),
                )

                affected_items = extract_affected(record)
                repo.replace_symbols(advisory_id, affected_items)

                stats.imported += 1
                stats.symbols_imported += len(affected_items)

                if stats.imported % _BATCH_SIZE == 0:
                    conn.commit()

            if self.incremental and sync_start is not None:
                _write_last_sync(conn, sync_start)

        stats.elapsed_seconds = time.monotonic() - start_time
        return stats


def sync_osv(
    db_path: str | Path,
    source: str | Path,
    incremental: bool = False,
) -> ImportStats:
    """Entry point for syncing OSV database from a local file or directory."""
    source_str = str(source)
    if source_str.startswith(_NETWORK_SCHEMES):
        raise OSVError(
            f"Network download is not supported: {source}. "
            "Please provide a path to a local OSV JSONL file or directory."
        )

    source_path = Path(source).expanduser().resolve()
    importer = OSVImporter(db_path, incremental=incremental)

    if source_path.is_file():
        return importer.import_file(source_path)

    if source_path.is_dir():
        aggregated = ImportStats()
        start = time.monotonic()
        for f in sorted(source_path.glob("*.jsonl")):
            file_stats = importer.import_file(f)
            aggregated.total += file_stats.total
            aggregated.imported += file_stats.imported
            aggregated.skipped_ecosystem += file_stats.skipped_ecosystem
            aggregated.skipped_malformed += file_stats.skipped_malformed
            aggregated.skipped_up_to_date += file_stats.skipped_up_to_date
            aggregated.symbols_imported += file_stats.symbols_imported
        aggregated.elapsed_seconds = time.monotonic() - start
        return aggregated

    raise OSVError(f"OSV source path does not exist: {source_path}")
