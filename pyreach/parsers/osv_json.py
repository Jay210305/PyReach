"""OSV JSON record parser and version range evaluator."""

import re
from decimal import ROUND_CEILING, Decimal
from typing import Any

from pyreach.osv.mapper import AffectedSymbol, Vulnerability
from pyreach.parsers.manifest import normalize_name

_SEVERITY_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

# CVSS version preference: v3 (v3.1/v3.0) first, then v4, then v2 (S1-T5 pitfalls).
_CVSS_ORDER = {"CVSS_V3": 0, "CVSS_V4": 1, "CVSS_V2": 2}

# CVSS v3.x base metric weights (spec §5.1). Decimal avoids float round-off in
# the round-up-to-one-decimal step of the base score.
_AV = {"N": Decimal("0.85"), "A": Decimal("0.62"), "L": Decimal("0.55"), "P": Decimal("0.20")}
_AC = {"L": Decimal("0.77"), "H": Decimal("0.44")}
_UI = {"N": Decimal("0.85"), "R": Decimal("0.62")}
_PR_U = {"N": Decimal("0.85"), "L": Decimal("0.62"), "H": Decimal("0.27")}
_PR_C = {"N": Decimal("0.85"), "L": Decimal("0.68"), "H": Decimal("0.50")}
_CIA = {"N": Decimal("0.0"), "L": Decimal("0.22"), "H": Decimal("0.56")}


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


def _cvss31_base_score(vector: str) -> float | None:
    """Compute the CVSS v3.0/v3.1 base score from a vector string.

    Returns ``None`` for non-v3 vectors (v2/v4 base scoring is out of scope for
    Sprint 1; S1-T5 §5.1 targets v3.1).
    """
    if not vector.startswith("CVSS:3"):
        return None

    metrics: dict[str, str] = {}
    for part in vector.split("/")[1:]:
        key, _, value = part.partition(":")
        metrics[key] = value

    scope = metrics.get("S", "U")
    try:
        av = _AV[metrics["AV"]]
        ac = _AC[metrics["AC"]]
        ui = _UI[metrics["UI"]]
        pr = (_PR_C if scope == "C" else _PR_U)[metrics["PR"]]
        c = _CIA[metrics["C"]]
        i = _CIA[metrics["I"]]
        a = _CIA[metrics["A"]]
    except KeyError:
        return None

    iss = Decimal(1) - (Decimal(1) - c) * (Decimal(1) - i) * (Decimal(1) - a)
    if scope == "U":
        impact = Decimal("6.42") * iss
    else:
        impact = Decimal("7.52") * (iss - Decimal("0.029")) - Decimal("3.25") * (
            iss - Decimal("0.02")
        ) ** 15
    exploitability = Decimal("8.22") * av * ac * pr * ui

    if impact <= 0:
        return 0.0
    if scope == "U":
        base = impact + exploitability
    else:
        base = Decimal("1.08") * (impact + exploitability)
    base = min(base, Decimal(10)).quantize(Decimal("0.1"), rounding=ROUND_CEILING)
    return float(base)


def _severity_score(raw: Any) -> float | None:
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return _cvss31_base_score(value)
    return None


def _parse_severity(severity_list: Any) -> tuple[float | None, str | None]:
    if not isinstance(severity_list, list):
        return None, None
    entries = [s for s in severity_list if isinstance(s, dict)]
    entries.sort(key=lambda s: _CVSS_ORDER.get(str(s.get("type")), 99))
    for entry in entries:
        score = _severity_score(entry.get("score"))
        if score is not None:
            return score, map_cvss_score_to_level(score)
    return None, None


def _extract_cve_id(aliases: Any) -> str | None:
    if not isinstance(aliases, list):
        return None
    for alias in aliases:
        if isinstance(alias, str) and re.match(r"^CVE-\d{4}-\d+$", alias):
            return alias
    return None


def _database_severity(db_specific: Any) -> str | None:
    if isinstance(db_specific, dict):
        raw = db_specific.get("severity")
        if isinstance(raw, str) and raw.upper() in _SEVERITY_LEVELS:
            return raw.upper()
    return None


def _first_pypi_affected(record: dict[str, Any]) -> dict[str, Any] | None:
    affected_list = record.get("affected")
    if not isinstance(affected_list, list):
        return None
    for item in affected_list:
        if isinstance(item, dict):
            package = item.get("package")
            if isinstance(package, dict) and package.get("ecosystem") == "PyPI":
                return item
    return None


def is_pypi_record(record: dict[str, Any]) -> bool:
    """Return True if *record* declares at least one PyPI affected block."""
    return _first_pypi_affected(record) is not None


def _extract_symbols(item: dict[str, Any]) -> list[str]:
    symbols: list[str] = []
    eco_specific = item.get("ecosystem_specific")
    if isinstance(eco_specific, dict):
        imports = eco_specific.get("imports")
        if isinstance(imports, list):
            for imp in imports:
                if isinstance(imp, dict) and isinstance(imp.get("symbols"), list):
                    for s in imp["symbols"]:
                        if isinstance(s, str) and s not in symbols:
                            symbols.append(s)
        direct = eco_specific.get("symbols")
        if isinstance(direct, list):
            for s in direct:
                if isinstance(s, str) and s not in symbols:
                    symbols.append(s)
    return symbols or ["*"]


def _extract_ranges(item: dict[str, Any]) -> list[tuple[str | None, str | None, bool]]:
    """Return ``(introduced, upper_bound, upper_inclusive)`` tuples for one block.

    Walks ``ranges[]`` accumulating one range per ``introduced`` ->
    ``fixed``/``last_affected`` pair, honoring explicit ``versions[]`` when no
    ranges are present. ``last_affected`` is inclusive, ``fixed`` is exclusive.
    """
    ranges: list[tuple[str | None, str | None, bool]] = []

    range_list = item.get("ranges")
    if isinstance(range_list, list):
        for r in range_list:
            if not isinstance(r, dict) or r.get("type") not in {"ECOSYSTEM", "SEMVER"}:
                continue
            events = r.get("events")
            if not isinstance(events, list):
                continue
            introduced: str | None = None
            for event in events:
                if not isinstance(event, dict):
                    continue
                if "introduced" in event:
                    introduced = str(event["introduced"])
                elif "fixed" in event:
                    ranges.append((introduced, str(event["fixed"]), False))
                    introduced = None
                elif "last_affected" in event:
                    ranges.append((introduced, str(event["last_affected"]), True))
                    introduced = None
            if introduced is not None:
                ranges.append((introduced, None, False))

    if ranges:
        return ranges

    versions = item.get("versions")
    if isinstance(versions, list):
        ranges = [(str(v), str(v), True) for v in versions if isinstance(v, str)]

    if not ranges:
        ranges = [(None, None, False)]
    return ranges


def extract_affected(record: dict[str, Any]) -> list[AffectedSymbol]:
    """Extract affected symbols and their version ranges from PyPI blocks.

    One :class:`AffectedSymbol` is emitted per (symbol, range) so multi-range
    advisories are preserved instead of collapsed to a single pair.
    """
    results: list[AffectedSymbol] = []
    affected_list = record.get("affected")
    if not isinstance(affected_list, list):
        return results

    for item in affected_list:
        if not isinstance(item, dict):
            continue
        package = item.get("package")
        if not isinstance(package, dict) or package.get("ecosystem") != "PyPI":
            continue

        for symbol in _extract_symbols(item):
            for introduced, upper, inclusive in _extract_ranges(item):
                results.append(AffectedSymbol(symbol, introduced, upper, inclusive))

    return results


def parse_osv_record(record: dict[str, Any]) -> Vulnerability | None:
    """Parse an OSV dictionary record into a :class:`Vulnerability`.

    Returns ``None`` for records missing required fields or with no PyPI
    affected block. Callers distinguish the two cases with
    :func:`is_pypi_record`.
    """
    osv_id = record.get("id")
    if not isinstance(osv_id, str) or not osv_id:
        return None

    pypi_affected = _first_pypi_affected(record)
    if pypi_affected is None:
        return None

    package_name_raw = pypi_affected.get("package", {}).get("name", "")
    if not package_name_raw:
        return None
    package_name = normalize_name(package_name_raw)

    cve_id = _extract_cve_id(record.get("aliases"))
    severity_score, severity_level = _parse_severity(record.get("severity"))
    if severity_level is None:
        severity_level = _database_severity(record.get("database_specific"))

    summary = str(record.get("summary", ""))

    affected = extract_affected(record)
    symbols = list(dict.fromkeys(a.symbol_fqn for a in affected)) or ["*"]
    introduced = next(
        (a.version_introduced for a in affected if a.version_introduced is not None), None
    )
    fixed = next((a.version_fixed for a in affected if a.version_fixed is not None), None)

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
