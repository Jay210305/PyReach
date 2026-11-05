"""SARIF v2.1.0 builder dataclasses (S4-T1) and serialization (S4-T2).

Every class maps to exactly one SARIF object and exposes ``to_dict()`` that
returns a JSON-serializable ``dict``. All custom PyReach metadata lives only
in ``properties`` (R3 mitigation).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import networkx as nx

from pyreach.exceptions import OutputError
from pyreach.parsers.manifest import normalize_name
from pyreach.reachability.contracts import ReachabilityResult

SARIF_SCHEMA_URL = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
)
SARIF_VERSION = "2.1.0"
_SCHEMA_RESOURCE = "sarif-schema-2.1.0.json"
TOOL_NAME = "PyReach"
TOOL_INFORMATION_URI = "https://github.com/lidercom/pyreach"


# ---------------------------------------------------------------------------
# Leaf helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SarifMessage:
    text: str

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text}


@dataclass(frozen=True)
class SarifArtifactLocation:
    uri: str
    uri_base_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"uri": self.uri}
        if self.uri_base_id is not None:
            d["uriBaseId"] = self.uri_base_id
        return d


@dataclass(frozen=True)
class SarifRegion:
    start_line: int | None = None
    start_column: int | None = None
    end_column: int | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {}
        if self.start_line is not None:
            d["startLine"] = self.start_line
        if self.start_column is not None:
            d["startColumn"] = self.start_column
        if self.end_column is not None:
            d["endColumn"] = self.end_column
        return d


@dataclass(frozen=True)
class SarifPhysicalLocation:
    artifact_location: SarifArtifactLocation
    region: SarifRegion | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"artifactLocation": self.artifact_location.to_dict()}
        if self.region is not None:
            region_dict = self.region.to_dict()
            if region_dict:
                d["region"] = region_dict
        return d


@dataclass(frozen=True)
class SarifLogicalLocation:
    fully_qualified_name: str
    kind: str = "function"

    def to_dict(self) -> dict[str, object]:
        return {"fullyQualifiedName": self.fully_qualified_name, "kind": self.kind}


@dataclass(frozen=True)
class SarifLocation:
    physical_location: SarifPhysicalLocation | None = None
    logical_locations: list[SarifLogicalLocation] = field(default_factory=list)
    message: SarifMessage | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {}
        if self.physical_location is not None:
            d["physicalLocation"] = self.physical_location.to_dict()
        if self.logical_locations:
            d["logicalLocations"] = [loc.to_dict() for loc in self.logical_locations]
        if self.message is not None:
            d["message"] = self.message.to_dict()
        return d


@dataclass(frozen=True)
class SarifThreadFlowLocation:
    location: SarifLocation
    kinds: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"location": self.location.to_dict()}
        if self.kinds:
            d["kinds"] = list(self.kinds)
        return d


@dataclass(frozen=True)
class SarifThreadFlow:
    locations: list[SarifThreadFlowLocation] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"locations": [loc.to_dict() for loc in self.locations]}


@dataclass(frozen=True)
class SarifCodeFlow:
    thread_flows: list[SarifThreadFlow] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"threadFlows": [tf.to_dict() for tf in self.thread_flows]}


@dataclass(frozen=True)
class SarifRule:
    id: str
    name: str
    short_description: SarifMessage
    full_description: SarifMessage
    default_level: str = "error"
    properties: dict[str, object] = field(default_factory=dict)
    help_text: SarifMessage | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "shortDescription": self.short_description.to_dict(),
            "fullDescription": self.full_description.to_dict(),
            "defaultConfiguration": {"level": self.default_level},
        }
        if self.help_text is not None:
            d["help"] = self.help_text.to_dict()
        if self.properties:
            d["properties"] = dict(self.properties)
        return d


@dataclass(frozen=True)
class SarifDriver:
    name: str
    version: str
    information_uri: str
    rules: list[SarifRule] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "name": self.name,
            "version": self.version,
            "informationUri": self.information_uri,
        }
        if self.rules:
            d["rules"] = [r.to_dict() for r in self.rules]
        return d


@dataclass(frozen=True)
class SarifTool:
    driver: SarifDriver

    def to_dict(self) -> dict[str, object]:
        return {"driver": self.driver.to_dict()}


@dataclass(frozen=True)
class SarifInvocation:
    execution_successful: bool = True
    arguments: list[str] | None = None
    working_directory_uri: str | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"executionSuccessful": self.execution_successful}
        if self.arguments is not None:
            d["arguments"] = list(self.arguments)
        if self.working_directory_uri is not None:
            d["workingDirectory"] = {"uri": self.working_directory_uri}
        return d


@dataclass(frozen=True)
class UriBase:
    uri: str

    def to_dict(self) -> dict[str, object]:
        return {"uri": self.uri}


@dataclass
class SarifResult:
    rule_id: str
    rule_index: int
    level: str
    message: SarifMessage
    locations: list[SarifLocation] = field(default_factory=list)
    code_flows: list[SarifCodeFlow] = field(default_factory=list)
    properties: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "ruleId": self.rule_id,
            "ruleIndex": self.rule_index,
            "level": self.level,
            "message": self.message.to_dict(),
        }
        if self.locations:
            d["locations"] = [loc.to_dict() for loc in self.locations]
        if self.code_flows:
            d["codeFlows"] = [cf.to_dict() for cf in self.code_flows]
        if self.properties:
            d["properties"] = dict(self.properties)
        return d


@dataclass
class SarifRun:
    tool: SarifTool
    results: list[SarifResult] = field(default_factory=list)
    invocations: list[SarifInvocation] = field(default_factory=list)
    original_uri_base_ids: dict[str, UriBase] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"tool": self.tool.to_dict()}
        if self.results:
            d["results"] = [r.to_dict() for r in self.results]
        else:
            d["results"] = []
        if self.invocations:
            d["invocations"] = [inv.to_dict() for inv in self.invocations]
        if self.original_uri_base_ids:
            d["originalUriBaseIds"] = {
                k: v.to_dict() for k, v in self.original_uri_base_ids.items()
            }
        return d


@dataclass
class SarifReport:
    runs: list[SarifRun] = field(default_factory=list)
    version: str = SARIF_VERSION
    schema_url: str = SARIF_SCHEMA_URL

    def to_dict(self) -> dict[str, object]:
        return {
            "$schema": self.schema_url,
            "version": self.version,
            "runs": [r.to_dict() for r in self.runs],
        }


# ---------------------------------------------------------------------------
# Rule catalog
# ---------------------------------------------------------------------------

RULE_CATALOG: list[SarifRule] = [
    SarifRule(
        id="PYREACH-REACHABLE-CVE",
        name="ReachableVulnerability",
        short_description=SarifMessage(
            text="A vulnerable dependency symbol is statically reachable from application code."
        ),
        full_description=SarifMessage(
            text=(
                "The application's call graph contains a directed path from a defined "
                "entry point to a function or method known to contain a security "
                "vulnerability. The vulnerable package version is installed and the code "
                "path is exploitable under static analysis assumptions."
            )
        ),
        default_level="error",
        properties={
            "category": "security",
            "precision": "high",
            "tags": ["security", "vulnerability", "reachability", "sca"],
        },
    ),
    SarifRule(
        id="PYREACH-POTENTIAL-CVE",
        name="PotentiallyReachableVulnerability",
        short_description=SarifMessage(
            text=(
                "A vulnerable dependency symbol may be reachable via dynamic or "
                "unresolved call paths."
            )
        ),
        full_description=SarifMessage(
            text=(
                "No static path was found, but dynamic constructs (eval, getattr, "
                "importlib) or unresolved imports prevent ruling out reachability. "
                "Conservative classification requires treating this as potentially reachable."
            )
        ),
        default_level="warning",
        properties={
            "category": "security",
            "precision": "medium",
            "tags": ["security", "vulnerability", "reachability", "dynamic"],
        },
    ),
    SarifRule(
        id="PYREACH-NOT-REACHABLE-CVE",
        name="NotReachableVulnerability",
        short_description=SarifMessage(
            text="A vulnerable dependency symbol is not reachable from application entry points."
        ),
        full_description=SarifMessage(
            text=(
                "Static analysis found no call path from any entry point to the "
                "vulnerable symbol, and no dynamic or unresolved import pattern "
                "prevents that conclusion."
            )
        ),
        default_level="note",
        properties={
            "category": "security",
            "precision": "high",
            "tags": ["security", "vulnerability", "reachability"],
        },
    ),
]

RULE_INDEX: dict[str, int] = {rule.id: idx for idx, rule in enumerate(RULE_CATALOG)}

STATUS_TO_RULE_ID: dict[str, str] = {
    "REACHABLE": "PYREACH-REACHABLE-CVE",
    "POTENTIALLY_REACHABLE": "PYREACH-POTENTIAL-CVE",
    "NOT_REACHABLE": "PYREACH-NOT-REACHABLE-CVE",
}

STATUS_TO_LEVEL: dict[str, str] = {
    "REACHABLE": "error",
    "POTENTIALLY_REACHABLE": "warning",
    "NOT_REACHABLE": "note",
}


# ---------------------------------------------------------------------------
# Schema helper
# ---------------------------------------------------------------------------


def load_sarif_schema(schema_path: Path | None = None) -> dict[str, object]:
    """Load the OASIS SARIF v2.1.0 schema.

    By default the schema ships inside the package (``pyreach/output``), so it
    is always available offline — no network fetch, no CWD-relative path.
    ``schema_path`` overrides this (tests point it at the fixture under
    ``tests/fixtures/sarif_schema/``).
    """
    if schema_path is not None:
        if not schema_path.is_file():
            raise FileNotFoundError(f"SARIF schema not found at {schema_path}")
        return json.loads(schema_path.read_text(encoding="utf-8"))
    resource = resources.files("pyreach.output").joinpath(_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_sarif_document(
    doc: dict[str, object], schema: dict[str, object] | None = None
) -> None:
    """Validate *doc* against the OASIS SARIF schema.

    Raises :class:`OutputError` with the failing element path on mismatch.
    """
    import jsonschema

    if schema is None:
        schema = load_sarif_schema()
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(p) for p in exc.absolute_path) or "(root)"
        raise OutputError(f"SARIF validation failed at {path}: {exc.message}") from exc


def _single_line(text: str) -> str:
    return " ".join(text.split())


def _project_root_uri(project_root: Path) -> str:
    uri = project_root.resolve().as_uri()
    return uri if uri.endswith("/") else uri + "/"


def write_report(path: Path | str, document: object) -> None:
    """Write a complete UTF-8 report atomically within its destination directory."""
    import os
    import tempfile

    target = Path(path)
    temporary: str | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, delete=False
        ) as f:
            temporary = f.name
            f.write(document if isinstance(document, str) else json.dumps(document, indent=2))
            f.write("\n")
        os.replace(temporary, target)
    except (OSError, ValueError, TypeError) as exc:
        raise OutputError(f"Cannot write report {target}: {exc}") from exc
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()


class SarifBuilder:
    """Accumulate :class:`ReachabilityResult`s into one SARIF v2.1.0 document.

    Node ``(file, line)`` metadata comes from the call graph when provided;
    path elements without metadata degrade to message-only locations (the
    schema permits omitting ``physicalLocation``).
    """

    def __init__(
        self,
        tool_version: str = "0.1.0",
        project_root: str | Path = ".",
        graph: nx.DiGraph | None = None,
        installed_versions: dict[str, str] | None = None,
        arguments: list[str] | None = None,
    ) -> None:
        self._tool_version = tool_version
        self._project_root = Path(project_root)
        self._root_resolved = self._project_root.resolve()
        self._graph = graph
        self._installed_versions = (
            {normalize_name(k): v for k, v in installed_versions.items()}
            if installed_versions
            else {}
        )
        self._arguments = (
            list(arguments) if arguments is not None else ["pyreach", str(self._project_root)]
        )
        self._pending: list[tuple[tuple[float, str, str, str, str], SarifResult]] = []

    def location(self, symbol: str) -> dict[str, Any]:
        return self._symbol_location(symbol).to_dict()

    def add_result(
        self,
        result: ReachabilityResult,
        *,
        include_not_reachable: bool = False,
        symbol: str | None = None,
        installed_version: str | None = None,
    ) -> None:
        """Map one result to a SARIF result, skipping ``NOT_REACHABLE`` by default."""
        if result.status == "NOT_REACHABLE" and not include_not_reachable:
            return
        target = self._resolve_symbol(result, symbol)
        rule_id = STATUS_TO_RULE_ID[result.status]
        sarif_result = SarifResult(
            rule_id=rule_id,
            rule_index=RULE_INDEX[rule_id],
            level=STATUS_TO_LEVEL[result.status],
            message=SarifMessage(text=self._message_text(result, target, installed_version)),
            locations=[self._symbol_location(target, fallback_to_app=True)],
            code_flows=self._code_flows(result),
            properties=self._properties(result, target, installed_version),
        )
        self._pending.append((self._sort_key(result, target), sarif_result))

    def build(self) -> dict[str, object]:
        """Return the full SARIF document as a JSON-serializable dict."""
        ordered = [item[1] for item in sorted(self._pending, key=lambda item: item[0])]
        driver = SarifDriver(
            name=TOOL_NAME,
            version=self._tool_version,
            information_uri=TOOL_INFORMATION_URI,
            rules=list(RULE_CATALOG),
        )
        root_uri = _project_root_uri(self._project_root)
        run = SarifRun(
            tool=SarifTool(driver=driver),
            results=ordered,
            invocations=[
                SarifInvocation(
                    execution_successful=True,
                    arguments=list(self._arguments),
                    working_directory_uri=root_uri,
                )
            ],
            original_uri_base_ids={"PROJECT_ROOT": UriBase(uri=root_uri)},
        )
        return SarifReport(runs=[run]).to_dict()

    def write(self, path: Path | str) -> None:
        """Validate against the OASIS schema, then write to *path* as UTF-8 JSON.

        Validation is a hard gate (R3): an invalid document raises
        :class:`OutputError` (exit 2) rather than shipping a SARIF the CI
        dashboard would reject.
        """
        doc = self.build()
        validate_sarif_document(doc)
        write_report(path, doc)

    @staticmethod
    def _resolve_symbol(result: ReachabilityResult, symbol: str | None) -> str:
        if symbol:
            return symbol
        if result.paths and result.paths[0]:
            return result.paths[0][-1]
        if result.vulnerability.affected_symbols:
            return result.vulnerability.affected_symbols[0]
        return result.vulnerability.package_name

    def _message_text(
        self,
        result: ReachabilityResult,
        symbol: str,
        installed_version: str | None,
    ) -> str:
        vuln = result.vulnerability
        cve = vuln.cve_id or vuln.osv_id
        version = installed_version or self._installed_versions.get(
            normalize_name(vuln.package_name)
        )
        pkg_part = f"{vuln.package_name}=={version}" if version else vuln.package_name
        if result.entry_points_reached:
            suffix = f" from {result.entry_points_reached[0]}"
        elif result.paths and result.paths[0]:
            suffix = f" from {result.paths[0][0]}"
        else:
            suffix = ""
        return _single_line(f"{cve} in {pkg_part}: {symbol} is {result.status}{suffix}")

    def _properties(
        self,
        result: ReachabilityResult,
        symbol: str,
        installed_version: str | None,
    ) -> dict[str, object]:
        vuln = result.vulnerability
        version = installed_version or self._installed_versions.get(
            normalize_name(vuln.package_name)
        )
        props: dict[str, object] = {
            "reachability": result.status,
            "osvId": vuln.osv_id,
            "packageName": vuln.package_name,
            "affectedSymbol": symbol,
        }
        if vuln.cve_id is not None:
            props["cveId"] = vuln.cve_id
        if version is not None:
            props["installedVersion"] = version
        if vuln.severity_score is not None:
            props["severityScore"] = vuln.severity_score
        if vuln.severity_level is not None:
            props["severityLevel"] = vuln.severity_level
        if result.status == "REACHABLE" and result.paths and result.paths[0]:
            props["pathDepth"] = len(result.paths[0]) - 1
        else:
            props["pathDepth"] = 0
        if result.status in ("POTENTIALLY_REACHABLE", "NOT_REACHABLE"):
            props["reason"] = _single_line(result.reasoning)
        return props

    @staticmethod
    def _sort_key(result: ReachabilityResult, symbol: str) -> tuple[float, str, str, str, str]:
        score = result.vulnerability.severity_score
        return (
            -(score if score is not None else -1.0),
            result.vulnerability.package_name.lower(),
            result.vulnerability.cve_id or "",
            result.vulnerability.osv_id,
            symbol,
        )

    def _node_file_line(self, fqn: str) -> tuple[str | None, int | None]:
        if self._graph is None or fqn not in self._graph:
            return None, None
        data = self._graph.nodes[fqn]
        file_path = data.get("file_path")
        line = data.get("line_number")
        return (
            str(file_path) if file_path is not None else None,
            int(line) if isinstance(line, int) else None,
        )

    def _artifact_location(self, file_path: str | None) -> SarifArtifactLocation | None:
        if not file_path:
            return None
        raw = file_path.replace("\\", "/")
        candidate = Path(raw)
        is_absolute = (
            candidate.is_absolute()
            or PurePosixPath(raw).is_absolute()
            or PureWindowsPath(raw).is_absolute()
        )
        if is_absolute:
            for base in (self._root_resolved, self._project_root):
                try:
                    return SarifArtifactLocation(
                        uri=candidate.relative_to(base.resolve()).as_posix(),
                        uri_base_id="PROJECT_ROOT",
                    )
                except ValueError:
                    continue
            return SarifArtifactLocation(uri=candidate.as_posix())
        if raw.split("/")[0] == "..":
            return SarifArtifactLocation(uri=candidate.as_posix())
        return SarifArtifactLocation(uri=candidate.as_posix(), uri_base_id="PROJECT_ROOT")

    def _physical_location(self, fqn: str) -> SarifPhysicalLocation | None:
        file_path, line = self._node_file_line(fqn)
        artifact = self._artifact_location(file_path)
        if artifact is None:
            return None
        region = SarifRegion(start_line=line) if isinstance(line, int) and line > 0 else None
        return SarifPhysicalLocation(
            artifact_location=artifact,
            region=region,
        )

    def _symbol_location(self, symbol: str, fallback_to_app: bool = False) -> SarifLocation:
        physical = self._physical_location(symbol)
        if physical is None and fallback_to_app and self._graph is not None:
            for node in sorted(self._graph):
                candidate = self._physical_location(node)
                if (
                    candidate is not None
                    and candidate.artifact_location.uri_base_id == "PROJECT_ROOT"
                ):
                    physical = candidate
                    break
        return SarifLocation(
            physical_location=physical,
            logical_locations=[SarifLogicalLocation(fully_qualified_name=symbol)],
        )

    def _thread_flow_location(
        self, fqn: str, *, kinds: list[str], text: str
    ) -> SarifThreadFlowLocation:
        return SarifThreadFlowLocation(
            location=SarifLocation(
                physical_location=self._physical_location(fqn),
                message=SarifMessage(text=_single_line(text)),
            ),
            kinds=list(kinds),
        )

    def _code_flows(self, result: ReachabilityResult) -> list[SarifCodeFlow]:
        if result.status != "REACHABLE" or not result.paths or not result.paths[0]:
            return []
        path = result.paths[0]
        locations: list[SarifThreadFlowLocation] = []
        last = len(path) - 1
        for i, fqn in enumerate(path):
            if last == 0:
                kinds = ["entryPoint", "vulnerableCall"]
                text = f"Entry point: {fqn} (VULNERABLE)"
            elif i == 0:
                kinds = ["entryPoint"]
                text = f"Entry point: {fqn}"
            elif i == last:
                kinds = ["vulnerableCall"]
                text = f"-> {fqn} (VULNERABLE)"
            else:
                kinds = ["call"]
                text = f"-> {fqn}"
            locations.append(self._thread_flow_location(fqn, kinds=kinds, text=text))
        return [SarifCodeFlow(thread_flows=[SarifThreadFlow(locations=locations)])]
