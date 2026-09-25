"""OSV JSONL streaming importer and synchronization."""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyreach.db.connection import get_db_connection, initialize_database
from pyreach.db.repositories import AdvisoryRepository
from pyreach.exceptions import OSVError
from pyreach.parsers.osv_json import extract_affected, parse_osv_record


@dataclass
class ImportStats:
    """Statistics collected during an OSV import run."""

    total: int = 0
    imported: int = 0
    skipped_ecosystem: int = 0
    skipped_malformed: int = 0
    symbols_imported: int = 0
    elapsed_seconds: float = 0.0


def iter_osv_records(path: Path) -> Iterator[tuple[dict[str, Any] | None, bool]]:
    """Yield records line-by-line from a JSONL file.

    Returns tuples of (record_dict_or_None, is_malformed).
    """
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
                if isinstance(record, dict):
                    yield record, False
                else:
                    yield None, True
            except json.JSONDecodeError:
                yield None, True


class OSVImporter:
    """Bulk importer for OSV vulnerability data into SQLite."""

    def __init__(self, db_path: str | Path, incremental: bool = False) -> None:
        self.db_path = Path(db_path)
        self.incremental = incremental

    def import_file(self, path: str | Path) -> ImportStats:
        """Stream an OSV JSONL file and insert/update advisory records."""
        file_path = Path(path)
        if not file_path.is_file():
            raise OSVError(f"OSV data file not found: {file_path}")

        stats = ImportStats()
        start_time = time.monotonic()

        initialize_database(self.db_path)
        with get_db_connection(self.db_path) as conn:
            repo = AdvisoryRepository(conn)
            last_sync: str | None = None
            if self.incremental:
                cursor = conn.execute("SELECT MAX(modified_date) FROM advisories;")
                row = cursor.fetchone()
                if row and row[0]:
                    last_sync = row[0]

            for record, is_malformed in iter_osv_records(file_path):
                stats.total += 1
                if is_malformed or record is None:
                    stats.skipped_malformed += 1
                    continue

                if self.incremental and last_sync:
                    record_modified = record.get("modified")
                    if record_modified and record_modified <= last_sync:
                        continue

                vuln = parse_osv_record(record)
                if vuln is None:
                    stats.skipped_ecosystem += 1
                    continue

                modified_date = record.get("modified")
                published_date = record.get("published")
                aliases = record.get("aliases")
                raw_json = json.dumps(record, ensure_ascii=False)

                advisory_id = repo.upsert(
                    advisory=vuln,
                    modified_date=modified_date,
                    published_date=published_date,
                    aliases=aliases,
                    raw_json=raw_json,
                )

                affected_items = extract_affected(record)
                repo.replace_symbols(advisory_id, affected_items)

                stats.imported += 1
                stats.symbols_imported += len(affected_items)

        stats.elapsed_seconds = time.monotonic() - start_time
        return stats


def sync_osv(
    db_path: str | Path,
    source: str | Path,
    incremental: bool = False,
) -> ImportStats:
    """Entry point for syncing OSV database from a local file or directory."""
    source_str = str(source)
    if source_str.startswith(("http://", "https://", "ftp://")):
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
            aggregated.symbols_imported += file_stats.symbols_imported
        aggregated.elapsed_seconds = time.monotonic() - start
        return aggregated

    raise OSVError(f"OSV source path does not exist: {source_path}")
