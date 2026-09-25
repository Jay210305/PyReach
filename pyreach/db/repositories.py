"""Database repositories for advisories and affected symbols."""

import json
import sqlite3

from pyreach.parsers.manifest import normalize_name
from pyreach.parsers.osv_json import Vulnerability, is_version_affected


class AdvisoryRepository:
    """Repository handling persistence and querying of OSV advisories."""

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
            "aliases": json.dumps(aliases or []),
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
        symbols: list[tuple[str, str | None, str | None]],
    ) -> None:
        """Replace all affected_symbols rows for the given advisory_id."""
        self._conn.execute("DELETE FROM affected_symbols WHERE advisory_id = ?;", (advisory_id,))
        insert_sql = """
            INSERT INTO affected_symbols (
                advisory_id, symbol_fqn, version_introduced, version_fixed
            )
            VALUES (?, ?, ?, ?);
        """
        seen: set[tuple[str, str | None, str | None]] = set()
        for sym, intro, fixed in symbols:
            key = (sym, intro, fixed)
            if key not in seen:
                seen.add(key)
                self._conn.execute(insert_sql, (advisory_id, sym, intro, fixed))

    def find_by_package_and_version(self, package_name: str, version: str) -> list[Vulnerability]:
        """Query advisories affecting a specific package and installed version."""
        norm_pkg = normalize_name(package_name)
        sql = "SELECT * FROM advisories WHERE package_name = ?;"
        cursor = self._conn.execute(sql, (norm_pkg,))
        rows = cursor.fetchall()
        matching: list[Vulnerability] = []

        for row in rows:
            advisory_id = row["id"]
            sym_cursor = self._conn.execute(
                "SELECT symbol_fqn, version_introduced, version_fixed "
                "FROM affected_symbols WHERE advisory_id = ?;",
                (advisory_id,),
            )
            sym_rows = sym_cursor.fetchall()
            is_affected = False
            symbols: list[str] = []
            intro_val: str | None = None
            fixed_val: str | None = None

            for sym_row in sym_rows:
                s_fqn = sym_row["symbol_fqn"]
                intro = sym_row["version_introduced"]
                fixed = sym_row["version_fixed"]
                if s_fqn not in symbols:
                    symbols.append(s_fqn)
                if intro_val is None and intro is not None:
                    intro_val = intro
                if fixed_val is None and fixed is not None:
                    fixed_val = fixed

                if is_version_affected(version, intro, fixed):
                    is_affected = True

            if not sym_rows:
                is_affected = True
                symbols = ["*"]

            if is_affected:
                matching.append(
                    Vulnerability(
                        osv_id=row["osv_id"],
                        cve_id=row["cve_id"],
                        package_name=row["package_name"],
                        severity_score=row["severity_score"],
                        severity_level=row["severity_level"],
                        summary=row["summary"] or "",
                        affected_symbols=symbols,
                        version_introduced=intro_val,
                        version_fixed=fixed_val,
                    )
                )

        return matching
