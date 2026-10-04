"""OSV advisory mapper: the ``Vulnerability`` contract and package/version lookup.

This module owns the :class:`Vulnerability` data contract (AGENTS.md §6, spec
§3.4) and the query-side mapping of installed packages to the advisories that
affect them (doc 02 §OSV Mapper, doc 03 §2 ``osv/mapper.py``). The JSON parsing
half lives in :mod:`pyreach.parsers.osv_json`; the persistence half lives in
:mod:`pyreach.db.repositories`.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from packaging.version import InvalidVersion, Version

from pyreach.parsers.manifest import normalize_name


@dataclass
class Vulnerability:
    """A single vulnerability advisory loaded from the local OSV database."""

    osv_id: str
    cve_id: str | None
    package_name: str
    severity_score: float | None
    severity_level: str | None  # LOW, MEDIUM, HIGH, CRITICAL
    summary: str
    affected_symbols: list[str]  # e.g., ["requests.sessions.Session.request"]
    version_introduced: str | None
    version_fixed: str | None


@dataclass(frozen=True)
class AffectedSymbol:
    """A vulnerable symbol bound to one affected version range.

    ``version_fixed`` is the range's upper bound: exclusive when
    ``version_fixed_inclusive`` is ``False`` (OSV ``fixed``) and inclusive when
    it is ``True`` (OSV ``last_affected``). A range with neither bound means
    "all versions" and is represented as ``(None, None)``.
    """

    symbol_fqn: str
    version_introduced: str | None
    version_fixed: str | None
    version_fixed_inclusive: bool = False


def is_version_affected(
    version: str,
    introduced: str | None,
    fixed: str | None,
    fixed_inclusive: bool = False,
) -> bool:
    """Return True if *version* falls within the affected range.

    The lower bound (``introduced``) is inclusive. The upper bound (``fixed``)
    is exclusive unless ``fixed_inclusive`` is set (OSV ``last_affected``).
    Unparseable bounds resolve conservatively to ``True`` to avoid false
    negatives.
    """
    try:
        v = Version(version)
    except InvalidVersion:
        return True

    if introduced:
        try:
            if v < Version(introduced):
                return False
        except InvalidVersion:
            return True

    if fixed:
        try:
            f = Version(fixed)
        except InvalidVersion:
            return True
        if fixed_inclusive:
            if v > f:
                return False
        elif v >= f:
            return False

    return True


class VulnerabilityMapper:
    """Query SQLite for advisories affecting an installed package/version."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def find_by_package_and_version(
        self, package_name: str, version: str
    ) -> list[Vulnerability]:
        """Return advisories affecting *package_name* at *version*.

        An advisory matches when any of its stored ``(introduced, fixed)``
        range rows contains *version*; version evaluation is delegated to
        :func:`is_version_affected`.
        """
        norm_pkg = normalize_name(package_name)
        rows = self._conn.execute(
            "SELECT * FROM advisories WHERE package_name = ?;", (norm_pkg,)
        ).fetchall()

        matching: list[Vulnerability] = []
        for row in rows:
            advisory_id = row["id"]
            sym_rows = self._conn.execute(
                "SELECT symbol_fqn, version_introduced, version_fixed, "
                "version_fixed_inclusive FROM affected_symbols WHERE advisory_id = ?;",
                (advisory_id,),
            ).fetchall()

            is_affected = not sym_rows
            symbols: list[str] = []
            intro_val: str | None = None
            fixed_val: str | None = None

            for sym_row in sym_rows:
                s_fqn = sym_row["symbol_fqn"]
                if s_fqn not in symbols:
                    symbols.append(s_fqn)
                intro = sym_row["version_introduced"]
                fixed = sym_row["version_fixed"]
                inclusive = bool(sym_row["version_fixed_inclusive"])
                if intro_val is None and intro is not None:
                    intro_val = intro
                if fixed_val is None and fixed is not None:
                    fixed_val = fixed
                if is_version_affected(version, intro, fixed, inclusive):
                    is_affected = True

            if is_affected:
                matching.append(
                    Vulnerability(
                        osv_id=row["osv_id"],
                        cve_id=row["cve_id"],
                        package_name=row["package_name"],
                        severity_score=row["severity_score"],
                        severity_level=row["severity_level"],
                        summary=row["summary"] or "",
                        affected_symbols=symbols or ["*"],
                        version_introduced=intro_val,
                        version_fixed=fixed_val,
                    )
                )

        return matching
