"""OSV JSON record parser and version range evaluator."""

import re
from dataclasses import dataclass
from typing import Any

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


def map_cvss_score_to_level(score: float | None) -> str | None:
    """Map a numerical CVSS score to a qualitative severity level."""
    if score is None:
        return None
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


def is_version_affected(version: str, introduced: str | None, fixed: str | None) -> bool:
    """Return True if version falls within [introduced, fixed).

    If versions cannot be parsed, conservatively returns True to avoid false negatives.
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
            if v >= Version(fixed):
                return False
        except InvalidVersion:
            return True

    return True


def extract_affected(record: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    """Extract (symbol_fqn, version_introduced, version_fixed) tuples from PyPI affected blocks."""
    results: list[tuple[str, str | None, str | None]] = []
    affected_list = record.get("affected")
    if not isinstance(affected_list, list):
        return results

    for item in affected_list:
        if not isinstance(item, dict):
            continue
        package = item.get("package")
        if not isinstance(package, dict) or package.get("ecosystem") != "PyPI":
            continue

        introduced: str | None = None
        fixed: str | None = None
        for r in item.get("ranges", []):
            if isinstance(r, dict) and r.get("type") in {"ECOSYSTEM", "SEMVER"}:
                for event in r.get("events", []):
                    if "introduced" in event:
                        introduced = str(event["introduced"])
                    if "fixed" in event:
                        fixed = str(event["fixed"])
                    elif "last_affected" in event:
                        fixed = str(event["last_affected"])

        symbols: list[str] = []
        eco_specific = item.get("ecosystem_specific")
        if isinstance(eco_specific, dict):
            imports = eco_specific.get("imports")
            if isinstance(imports, list):
                for imp in imports:
                    if isinstance(imp, dict) and "symbols" in imp:
                        for s in imp["symbols"]:
                            if isinstance(s, str) and s not in symbols:
                                symbols.append(s)
            direct_symbols = eco_specific.get("symbols")
            if isinstance(direct_symbols, list):
                for s in direct_symbols:
                    if isinstance(s, str) and s not in symbols:
                        symbols.append(s)

        if not symbols:
            symbols = ["*"]

        for s in symbols:
            results.append((s, introduced, fixed))

    return results


def parse_osv_record(record: dict[str, Any]) -> Vulnerability | None:
    """Parse a single OSV dictionary record into a Vulnerability object if it affects PyPI."""
    osv_id = record.get("id")
    if not isinstance(osv_id, str) or not osv_id:
        return None

    affected_list = record.get("affected")
    if not isinstance(affected_list, list) or not affected_list:
        return None

    pypi_affected: dict[str, Any] | None = None
    for item in affected_list:
        if isinstance(item, dict):
            pkg = item.get("package")
            if isinstance(pkg, dict) and pkg.get("ecosystem") == "PyPI":
                pypi_affected = item
                break

    if pypi_affected is None:
        return None

    package_name_raw = pypi_affected.get("package", {}).get("name", "")
    if not package_name_raw:
        return None
    package_name = normalize_name(package_name_raw)

    cve_id: str | None = None
    aliases = record.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str) and re.match(r"^CVE-\d{4}-\d+$", alias):
                cve_id = alias
                break

    severity_score: float | None = None
    severity_level: str | None = None

    severity_list = record.get("severity")
    if isinstance(severity_list, list):
        for sev in severity_list:
            if isinstance(sev, dict):
                score_val = sev.get("score")
                if isinstance(score_val, (int, float)):
                    severity_score = float(score_val)
                    break
                elif isinstance(score_val, str):
                    try:
                        severity_score = float(score_val)
                        break
                    except ValueError:
                        pass

    db_specific = record.get("database_specific")
    if isinstance(db_specific, dict):
        raw_level = db_specific.get("severity")
        if isinstance(raw_level, str) and raw_level.upper() in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }:
            severity_level = raw_level.upper()

    if severity_score is not None and severity_level is None:
        severity_level = map_cvss_score_to_level(severity_score)

    summary = str(record.get("summary", ""))

    affected_items = extract_affected(record)
    symbols: list[str] = []
    introduced: str | None = None
    fixed: str | None = None

    for sym, intro, fix in affected_items:
        if sym not in symbols:
            symbols.append(sym)
        if introduced is None and intro is not None:
            introduced = intro
        if fixed is None and fix is not None:
            fixed = fix

    if not symbols:
        symbols = ["*"]

    return Vulnerability(
        osv_id=osv_id,
        cve_id=cve_id,
        package_name=package_name,
        severity_score=severity_score,
        severity_level=severity_level,
        summary=summary,
        affected_symbols=symbols,
        version_introduced=introduced,
        version_fixed=fixed,
    )
