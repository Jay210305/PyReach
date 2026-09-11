# S4-T2 — Implement SARIF serialization with `codeFlows` for reachable paths

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 10 h |
| Dependencies | S4-T1 |
| Related docs | `07-sarif-and-cli-design.md` §1.3, §1.4, §1.5; `03-technical-specifications.md` §7; `10-risk-and-contingency-plan.md` §2 R3 |

## Purpose

Turn `ReachabilityResult`s into a validated SARIF v2.1.0 document, including full call paths as
`codeFlows`. This is the artifact Lidercom's GitLab security dashboard consumes, so schema
conformance is a hard gate.

## Preconditions

- S4-T1 classes and schema fixture merged.
- `jsonschema>=4.0`.
- Sample `ReachabilityResult`s (from S3-T8 fixtures).

## Essential Sub-tasks

### 2.1 Implement the SARIF builder API (2 h)

In `pyreach/output/sarif.py`:

```python
class SarifBuilder:
    def __init__(self, tool_version: str, project_root: Path) -> None: ...
    def add_result(self, result: ReachabilityResult, *, include_not_reachable: bool) -> None: ...
    def build(self) -> dict: ...
    def write(self, path: Path) -> None: ...
```

- `build()` returns a plain `dict` ready for `json.dumps(..., indent=2)`.
- `write()` ensures the output directory exists and uses UTF-8.
- Deterministic ordering: sort results by `(severity desc, package, cve_id)`.

### 2.2 Map each result to a SARIF result (2.5 h)

Per `07-...md` §1.3:

- `REACHABLE` -> `ruleId="PYREACH-REACHABLE-CVE"`, `level="error"`.
- `POTENTIALLY_REACHABLE` -> `ruleId="PYREACH-POTENTIAL-CVE"`, `level="warning"`.
- `NOT_REACHABLE` -> omitted unless `include_not_reachable`, then `level="note"` with rule
  `PYREACH-NOT-REACHABLE-CVE`.
- `message.text` template:
  `"{cve} in {pkg}=={version}: {symbol} is {STATUS} from {entry}"`.
- `properties`: `reachability`, `cveId`, `osvId`, `packageName`, `installedVersion`,
  `severityScore`, `severityLevel`, `pathDepth`, `reason` (for potential).

### 2.3 Populate `locations` (1.5 h)

- `physicalLocation.artifactLocation.uri` = path relative to `PROJECT_ROOT`, forward slashes.
- `uriBaseId = "PROJECT_ROOT"`.
- `region.startLine` from the vulnerable symbol's node metadata (fallback: node line, else 1).
- `logicalLocations[].fullyQualifiedName` = symbol FQN, `kind="function"`.

### 2.4 Populate `codeFlows` for reachable paths (2.5 h)

For each reachable path (bounded to N):

```
codeFlows[0].threadFlows[0].locations[] = [
  { location: { physicalLocation, message: "Entry point: X" }, kinds: ["entryPoint"] },
  { location: { ..., message: "-> A" }, kinds: ["call"] },
  ...
  { location: { ..., message: "-> VULN (VULNERABLE)" }, kinds: ["vulnerableCall"] },
]
```

- Resolve each FQN to its `(file, line)` using the call graph node metadata.
- If a path element has no location, emit a message-only location (schema allows omitting
  `physicalLocation`).
- Ensure only one `codeFlow` per result in Phase 2 (keep it simple).

### 2.5 Add `invocations` and `originalUriBaseIds` (0.5 h)

- `invocations[0]` with `executionSuccessful`, `arguments`, `workingDirectory`.
- `originalUriBaseIds.PROJECT_ROOT.uri = file:///.../` with a trailing slash
  (`07-...md` §1.5).

### 2.6 Validate against the OASIS schema in tests (1.5 h)

Create `tests/unit/output/test_sarif_serialization.py`:

| Test | Assertion |
|------|-----------|
| `test_reachable_result_validates` | full doc validates against schema |
| `test_potential_result_validates` | warning rule + reason property |
| `test_not_reachable_omitted_by_default` | no note results |
| `test_not_reachable_included_flag` | note result present |
| `test_codeflow_ordering` | entryPoint -> call -> vulnerableCall |
| `test_rule_index_correct` | index points at matching rule |
| `test_uri_forward_slashes` | Windows path uses `/` |
| `test_original_uri_base_ids` | PROJECT_ROOT present |
| `test_write_creates_file` | file exists and is valid JSON |
| `test_deterministic_output` | byte-identical across two runs |

- Load the schema from the local fixture (never network in CI).
- Run `jsonschema.validate(instance=doc, schema=schema)` in every positive test.

### 2.7 Add a JSON-schema failure diagnostic (0.5 h)

- On validation failure in tests, print the `jsonschema.ValidationError` path to speed up
  debugging (this is a test-only helper).

## Deliverables

- `pyreach/output/sarif.py` — full `SarifBuilder`.
- `pyreach/output/__init__.py`
- `tests/unit/output/test_sarif_serialization.py`

## Acceptance Criteria

- Output validates against jsonschema SARIF v2.1.0 schema in tests. ✅ (roadmap S4-T2)
- `codeFlows` carry the full entry -> ... -> vulnerable path.
- Deterministic, portable (relative URIs) output.

## Verification

```bash
uv run pytest tests/unit/output -q
uv run pytest tests/unit/output --cov=pyreach.output --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Empty `results` array is valid; an empty `runs` array is **not** — always emit one run.
- `message.text` must be non-empty; SARIF requires `message` on results and locations.
- Character escaping in messages (newlines) — keep messages single-line.
- Paths outside `PROJECT_ROOT` (site-packages) should still be emitted; use absolute URIs or
  omit `uriBaseId` for those.
- GitLab maps `error` -> Critical/High and `warning` -> Medium (`09-...md` §4.1); confirm
  severity alignment.

## Risks / Scope Cuts

- **R3**: if GitLab rejects a field, remove the optional field rather than abandoning SARIF;
  keep `properties` for extras. Fallback JSON format exists but is not preferred.

## Definition of Done

- [ ] Builder + tests merged.
- [ ] Every output validates against the cached schema.
- [ ] `codeFlows` complete for reachable results.
- [ ] Coverage >=80% on `output/sarif.py`.
