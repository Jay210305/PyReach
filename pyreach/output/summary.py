"""Summary metrics without equating static discards with measured human time savings."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from pyreach.reachability.contracts import ReachabilityResult


def summarize(results: dict[tuple[str, str], ReachabilityResult]) -> dict[str, Any]:
    counts = {status: 0 for status in ("REACHABLE", "POTENTIALLY_REACHABLE", "NOT_REACHABLE")}
    advisories: dict[tuple[str, str], list[str]] = {}
    rows = []
    for (identifier, symbol), result in sorted(results.items()):
        counts[result.status] += 1
        advisories.setdefault((result.vulnerability.package_name, identifier), []).append(
            result.status
        )
        rows.append({**asdict(result), "symbol": symbol})
    discarded = sum(all(x == "NOT_REACHABLE" for x in statuses) for statuses in advisories.values())
    return {
        "results": rows,
        "summary": {
            **counts,
            "total_symbols": len(results),
            "total_advisories": len(advisories),
            "discarded_advisories": discarded,
            "reduction_percent": round(100 * discarded / len(advisories), 2) if advisories else 0.0,
            "manual_time_saved_minutes": None,
        },
    }


def text_summary(document: dict[str, Any]) -> str:
    counts = document["summary"]
    lines = ["PyReach - Static reachability report", *[f"{k}: {v}" for k, v in counts.items()]]
    for row in document["results"]:
        lines.append(
            f"[{row['status']}] {row['vulnerability']['osv_id']} "
            f"{row['symbol']}: {row['reasoning']}"
        )
        lines.extend("  " + " -> ".join(path) for path in row["paths"])
    lines.extend(f"[WARNING] {item}" for item in document.get("diagnostics", []))
    return "\n".join(lines)
