"""Database repositories for advisories and affected symbols."""

import json
import sqlite3

from pyreach.osv.mapper import AffectedSymbol, Vulnerability


class AdvisoryRepository:
    """Repository handling persistence of OSV advisories."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self,
        advisory: Vulnerability,
        modified_date: str | None = None,
        published_date: str | None = None,
        aliases: list[str] | None = None,
        raw_json: str | None = None,
    ) -> int:
        """Insert or update an advisory record and return its primary key id."""
        sql = """
            INSERT INTO advisories (
                osv_id, cve_id, package_name, ecosystem,
                severity_score, severity_level, summary,
                published_date, aliases, modified_date, raw_json
            )
            VALUES (
                :osv_id, :cve_id, :package_name, :ecosystem,
                :severity_score, :severity_level, :summary,
                :published_date, :aliases, :modified_date, :raw_json
            )
            ON CONFLICT(osv_id) DO UPDATE SET
                cve_id = excluded.cve_id,
                package_name = excluded.package_name,
                severity_score = excluded.severity_score,
                severity_level = excluded.severity_level,
                summary = excluded.summary,
                published_date = excluded.published_date,
                aliases = excluded.aliases,
                modified_date = excluded.modified_date,
                raw_json = excluded.raw_json;
        """
        params = {
            "osv_id": advisory.osv_id,
            "cve_id": advisory.cve_id,
            "package_name": advisory.package_name,
            "ecosystem": "PyPI",
            "severity_score": advisory.severity_score,
            "severity_level": advisory.severity_level,
            "summary": advisory.summary,
            "published_date": published_date,
            "aliases": json.dumps(aliases if isinstance(aliases, list) else []),
            "modified_date": modified_date,
            "raw_json": raw_json,
        }
        self._conn.execute(sql, params)
        row = self._conn.execute(
            "SELECT id FROM advisories WHERE osv_id = ?;", (advisory.osv_id,)
        ).fetchone()
        return int(row[0])

    def replace_symbols(
        self,
        advisory_id: int,
        symbols: list[AffectedSymbol],
    ) -> None:
        """Replace all affected_symbols rows for the given advisory_id."""
        self._conn.execute("DELETE FROM affected_symbols WHERE advisory_id = ?;", (advisory_id,))
        insert_sql = """
            INSERT INTO affected_symbols (
                advisory_id, symbol_fqn, version_introduced, version_fixed,
                version_fixed_inclusive
            )
            VALUES (?, ?, ?, ?, ?);
        """
        seen: set[tuple[str, str | None, str | None, bool]] = set()
        for symbol in symbols:
            key = (
                symbol.symbol_fqn,
                symbol.version_introduced,
                symbol.version_fixed,
                symbol.version_fixed_inclusive,
            )
            if key not in seen:
                seen.add(key)
                self._conn.execute(
                    insert_sql,
                    (
                        advisory_id,
                        symbol.symbol_fqn,
                        symbol.version_introduced,
                        symbol.version_fixed,
                        int(symbol.version_fixed_inclusive),
                    ),
                )
