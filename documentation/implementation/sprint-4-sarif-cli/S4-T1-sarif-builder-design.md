# S4-T1 — Design SARIF builder classes mapping PyReach results to OASIS schema

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 6 h |
| Dependencies | S3-T5, S3-T6 (result model) |
| Related docs | `07-sarif-and-cli-design.md` §1; `03-technical-specifications.md` §7; `10-risk-and-contingency-plan.md` §2 R3 |

## Purpose

Design the object model that converts internal `ReachabilityResult`s into SARIF v2.1.0 before
writing any JSON string. Risk **R3** (schema rejection) is mitigated here by mapping to the
OASIS schema up front and validating with `jsonschema` from day one.

## Preconditions

- `ReachabilityResult`, `Vulnerability` contracts available.
- `jsonschema>=4.0` installed.
- Cached SARIF schema fixture available (or fetchable once; see 1.4).

## Essential Sub-tasks

### 1.1 Produce a class diagram (1.5 h)

In `documentation/study/sarif-design.md` or the PR description, define classes:

```
SarifReport
├── schema_url: str
├── version: "2.1.0"
├── runs: list[SarifRun]
│
SarifRun
├── tool: SarifTool
├── results: list[SarifResult]
├── invocations: list[SarifInvocation]
├── original_uri_base_ids: dict[str, UriBase]
│
SarifTool -> SarifDriver { name, version, information_uri, rules: list[SarifRule] }
SarifRule { id, name, short_description, full_description, default_level, properties }
SarifResult { rule_id, rule_index, level, message, locations, code_flows, properties }
SarifLocation { physical_location, logical_locations }
SarifCodeFlow { thread_flows: list[SarifThreadFlow] }
SarifThreadFlow { locations: list[SarifThreadFlowLocation] }
```

- Each class maps to exactly one SARIF object; no class emits nested dicts ad hoc.
- All classes are plain dataclasses with `to_dict()` methods (JSON-serializable).

### 1.2 Define the rule catalog (1 h)

Three rules, mirroring `07-...md` §1.2:

| Rule ID | Level | Used for |
|---------|-------|----------|
| `PYREACH-REACHABLE-CVE` | `error` | `REACHABLE` |
| `PYREACH-POTENTIAL-CVE` | `warning` | `POTENTIALLY_REACHABLE` |
| `PYREACH-NOT-REACHABLE-CVE` | `note` | `NOT_REACHABLE` when `--include-all` |

- Provide a `RULE_CATALOG` constant with `rule_index` matching insertion order.
- Custom metadata goes only in `properties` (R3 mitigation).

### 1.3 Define the result mapping contract (1.5 h)

Document the exact field mapping (from `07-...md` §1.3, `03-...md` §7):

| PyReach | SARIF |
|---------|-------|
| vulnerability | `result.message`, `result.properties` |
| status | `result.level` + `result.ruleId` |
| call path | `result.codeFlows[].threadFlows[].locations[]` |
| source location | `result.locations[].physicalLocation` |
| symbol FQN | `result.locations[].logicalLocations[].fullyQualifiedName` |
| base path | `originalUriBaseIds.PROJECT_ROOT` |

- Path entries get `kinds`: first = `entryPoint`, middle = `call`, last = `vulnerableCall`.
- `artifactLocation.uriBaseId = "PROJECT_ROOT"` for portability (`07-...md` §1.5).

### 1.4 Establish the schema-validation fixture (1 h)

- Cache `sarif-schema-2.1.0.json` under `tests/fixtures/sarif_schema/`.
- Add a `load_sarif_schema()` helper that reads the local file and only fetches if missing.
- Add a smoke test that the schema fixture parses and contains `definitions`.

### 1.5 Write design-validation tests (1 h)

Create `tests/unit/output/test_sarif_model.py`:

| Test | Assertion |
|------|-----------|
| `test_report_minimal_validates` | empty-results report validates against schema |
| `test_rule_index_matches_catalog` | `ruleIndex` consistent with `rules[]` |
| `test_every_class_to_dict_json_serializable` | `json.dumps` succeeds |
| `test_level_mapping` | status -> level correct |
| `test_properties_only_custom_metadata` | no non-standard top-level keys |

## Deliverables

- Class design document.
- `pyreach/output/sarif.py` — dataclass skeletons with `to_dict()`.
- `tests/fixtures/sarif_schema/sarif-schema-2.1.0.json`.
- `tests/unit/output/test_sarif_model.py`.

## Acceptance Criteria

- Class diagram reviewed by Julio. ✅ (roadmap S4-T1)
- Minimal report validates against the OASIS schema.
- Mapping rules match `03-technical-specifications.md` §7 exactly.

## Verification

```bash
uv run pytest tests/unit/output/test_sarif_model.py -q
python -c "import json,jsonschema; jsonschema.validate(json.load(open('minimal.sarif')), json.load(open('tests/fixtures/sarif_schema/sarif-schema-2.1.0.json')))"
```

## Edge Cases & Pitfalls

- SARIF requires `$schema` and `version` strings to match exactly; a trailing slash breaks some
  consumers.
- `ruleIndex` is optional but, if present, must point at the right `rules[]` entry.
- `properties` is a free-form object, but `level` must be one of `none|note|warning|error`.
- URIs must use forward slashes even on Windows.

## Risks / Scope Cuts

- **R3**: if the schema proves restrictive, keep all custom data under `properties` and never
  invent top-level fields. Fallback is the `json` output format (`10-...md` §2 R3).

## Definition of Done

- [ ] Class design reviewed by Julio.
- [ ] Skeleton `to_dict()` classes merged.
- [ ] Schema fixture cached.
- [ ] Design tests green.
