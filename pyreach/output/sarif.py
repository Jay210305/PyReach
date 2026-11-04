"""Deterministic SARIF 2.1.0 serialization without fabricated source regions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import networkx as nx

from pyreach.exceptions import OutputError
from pyreach.reachability.contracts import ReachabilityResult

RULES = [
    ("REACHABLE", "PYREACH-REACHABLE-CVE", "error"),
    ("POTENTIALLY_REACHABLE", "PYREACH-POTENTIAL-CVE", "warning"),
    ("NOT_REACHABLE", "PYREACH-NOT-REACHABLE-CVE", "note"),
]


def write_report(path: Path, document: object) -> None:
    """Write a complete UTF-8 report atomically within its destination directory."""
    import os
    import tempfile

    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as f:
            temporary = f.name
            f.write(document if isinstance(document, str) else json.dumps(document, indent=2))
            f.write("\n")
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError) as exc:
        raise OutputError(f"Cannot write report {path}: {exc}") from exc
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()


class SarifBuilder:
    def __init__(
        self, tool_version: str, project_root: Path, graph: nx.DiGraph | None = None
    ) -> None:
        self.version = tool_version
        self.root = project_root.resolve()
        self.graph = graph if graph is not None else nx.DiGraph()
        self._results: list[dict[str, Any]] = []

    def location(self, symbol: str) -> dict[str, Any]:
        location: dict[str, Any] = {
            "logicalLocations": [{"fullyQualifiedName": symbol, "kind": "function"}],
            "message": {"text": symbol},
        }
        attrs = self.graph.nodes.get(symbol, {})
        file = attrs.get("file_path")
        if file:
            path = Path(file).resolve()
            artifact: dict[str, str]
            if path.is_relative_to(self.root):
                artifact = {
                    "uri": quote(path.relative_to(self.root).as_posix()),
                    "uriBaseId": "PROJECT_ROOT",
                }
            else:
                artifact = {"uri": path.as_uri()}
            physical: dict[str, Any] = {"artifactLocation": artifact}
            line = attrs.get("line_number")
            if isinstance(line, int) and line > 0:
                physical["region"] = {"startLine": line}
            location["physicalLocation"] = physical
        return location

    def add_result(
        self,
        result: ReachabilityResult,
        *,
        include_not_reachable: bool = False,
        symbol: str | None = None,
        installed_version: str = "unknown",
    ) -> None:
        if result.status == "NOT_REACHABLE" and not include_not_reachable:
            return
        symbol = symbol or result.vulnerability.affected_symbols[0]
        index = next(i for i, row in enumerate(RULES) if row[0] == result.status)
        _, rule, level = RULES[index]
        vuln = result.vulnerability
        item: dict[str, Any] = {
            "ruleId": rule,
            "ruleIndex": index,
            "level": level,
            "message": {
                "text": (
                    f"{vuln.osv_id} in {vuln.package_name}=={installed_version}: "
                    f"{symbol} is {result.status}. {result.reasoning}"
                )
            },
            "locations": [self.location(symbol)],
            "properties": {
                "reachability": result.status,
                "cveId": vuln.cve_id,
                "osvId": vuln.osv_id,
                "packageName": vuln.package_name,
                "installedVersion": installed_version,
                "severityScore": vuln.severity_score,
                "severityLevel": vuln.severity_level,
                "reason": result.reasoning,
                "symbol": symbol,
                "pathDepth": min((len(p) - 1 for p in result.paths), default=0),
            },
        }
        if result.paths:
            item["codeFlows"] = [
                {
                    "threadFlows": [
                        {
                            "locations": [
                                {
                                    "location": self.location(fqn),
                                    "kinds": [
                                        "entryPoint"
                                        if j == 0
                                        else "vulnerableCall"
                                        if j == len(path) - 1
                                        else "call"
                                    ],
                                }
                                for j, fqn in enumerate(path)
                            ]
                        }
                        for path in result.paths
                    ]
                }
            ]
        self._results.append(item)

    def build(self) -> dict[str, Any]:
        ordered = sorted(
            self._results,
            key=lambda x: (
                -(x["properties"]["severityScore"] or 0),
                x["properties"]["packageName"],
                x["properties"]["osvId"],
                x["properties"]["symbol"],
            ),
        )
        return {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "PyReach",
                            "version": self.version,
                            "rules": [
                                {
                                    "id": row[1],
                                    "shortDescription": {"text": row[0]},
                                    "defaultConfiguration": {"level": row[2]},
                                }
                                for row in RULES
                            ],
                        }
                    },
                    "originalUriBaseIds": {
                        "PROJECT_ROOT": {"uri": self.root.as_uri().rstrip("/") + "/"}
                    },
                    "invocations": [{"executionSuccessful": True}],
                    "results": ordered,
                }
            ],
        }

    def write(self, path: Path) -> None:
        write_report(path, self.build())
