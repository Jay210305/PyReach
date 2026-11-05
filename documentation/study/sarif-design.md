# SARIF Builder Design — S4-T1

> Maps PyReach `ReachabilityResult` to OASIS SARIF v2.1.0. Mitigates R3 (schema rejection).

## 1. Class Diagram

```
SarifReport
├── $schema: str = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
├── version: "2.1.0"
├── runs: list[SarifRun]

SarifRun
├── tool: SarifTool
├── results: list[SarifResult]
├── invocations: list[SarifInvocation]
├── originalUriBaseIds: dict[str, UriBase]   # {"PROJECT_ROOT": {"uri": "file:///..." }}

SarifTool
└── driver: SarifDriver
        ├── name: "PyReach"
        ├── version: str
        ├── informationUri: "https://github.com/lidercom/pyreach"
        └── rules: list[SarifRule]

SarifRule
├── id: str                        # PYREACH-REACHABLE-CVE | PYREACH-POTENTIAL-CVE | PYREACH-NOT-REACHABLE-CVE
├── name: str
├── shortDescription: SarifMessage
├── fullDescription: SarifMessage
├── help: SarifMessage | None
└── defaultConfiguration: {level: "error"|"warning"|"note"}
    properties: {category, precision, tags}

SarifResult
├── ruleId: str
├── ruleIndex: int                 # index into driver.rules
├── level: "error"|"warning"|"note"|"none"
├── message: SarifMessage
├── locations: list[SarifLocation]
├── codeFlows: list[SarifCodeFlow]   # only for REACHABLE
└── properties: dict               # reachability, cveId, osvId, packageName, ...

SarifLocation
├── physicalLocation: SarifPhysicalLocation
│     ├── artifactLocation: {uri, uriBaseId="PROJECT_ROOT"}
│     └── region: {startLine, startColumn, endColumn}
└── logicalLocations: list[SarifLogicalLocation]
      └── {fullyQualifiedName, kind="function"}

SarifCodeFlow
└── threadFlows: list[SarifThreadFlow]
      └── locations: list[SarifThreadFlowLocation]
            ├── location: SarifLocation (physicalLocation + message)
            └── kinds: ["entryPoint"] | ["call"] | ["vulnerableCall"]

SarifInvocation
├── executionSuccessful: bool
├── arguments: list[str]
└── workingDirectory: {uri}

UriBase
└── uri: str   # file:///absolute/path/
```

Each class is a plain dataclass with `to_dict() -> dict` returning JSON-serializable output.
No class emits nested dicts ad hoc; nesting is delegated to child `to_dict()`.

## 2. Rule Catalog

| Rule ID | Level | Name | Used for |
|---------|-------|------|----------|
| `PYREACH-REACHABLE-CVE` | `error` | `ReachableVulnerability` | `REACHABLE` |
| `PYREACH-POTENTIAL-CVE` | `warning` | `PotentiallyReachableVulnerability` | `POTENTIALLY_REACHABLE` |
| `PYREACH-NOT-REACHABLE-CVE` | `note` | `NotReachableVulnerability` | `NOT_REACHABLE` when `--include-all` |

Constant `RULE_CATALOG: list[SarifRule]` preserves insertion order; `ruleIndex` equals
list index. Custom metadata lives only in `properties` (R3).

## 3. Result Mapping Contract

| PyReach | SARIF |
|---------|-------|
| `vulnerability` | `result.message.text`, `result.properties` (osvId, cveId, packageName, severity, ...) |
| `status` | `result.level` + `result.ruleId` + `result.ruleIndex` |
| `call path` (list[str] FQNs) | `result.codeFlows[0].threadFlows[0].locations[]` with `kinds` |
| `source location` (file, line) | `result.locations[0].physicalLocation` |
| `symbol FQN` | `result.locations[0].logicalLocations[0].fullyQualifiedName` |
| `project root` | `originalUriBaseIds.PROJECT_ROOT.uri` (absolute `file://` + trailing `/`) |

Path kinds: first element = `entryPoint`, middle elements = `call`, last element =
`vulnerableCall`. All `artifactLocation.uri` values are relative to `PROJECT_ROOT`
with forward slashes; `uriBaseId = "PROJECT_ROOT"` for portability.

## 4. Validation Strategy

- Schema fixture cached at `tests/fixtures/sarif_schema/sarif-schema-2.1.0.json`.
- Helper `load_sarif_schema()` loads the schema bundled inside the package
  (`pyreach/output/sarif-schema-2.1.0.json`) via `importlib.resources`; it never
  touches the network. An explicit `schema_path` override is used by tests.
- Every output validated with `jsonschema.validate(instance=doc, schema=schema)`.

## 5. Edge Cases

- `$schema` and `version` strings must match exactly (no trailing slash).
- `ruleIndex` optional but when present must point at correct `rules[]` entry.
- `level` must be one of `none|note|warning|error` (schema enum).
- URIs use forward slashes even on Windows (`PurePosixPath`).
- Empty `results` array is valid; empty `runs` is not.
