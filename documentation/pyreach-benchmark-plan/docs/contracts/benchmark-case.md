# Contract C-CASE 1.0.0 — benchmark case

## Model
One JSON record per canonical case in `benchmarks/pyreach_eval/cases/` or generated manifest JSONL:
```json
{"schema_version":"1.0.0","case_id":"reach-001","suite":"controlled-reachability","source_id":"fixture-reach-001","case_kind":"reachability","project_relpath":".","entry_points":["app.main:run"],"target_symbols":["vulnpkg.parser:unsafe_load"],"advisory_id":"FIXTURE-001","expected_label":"reachable","expected_edges":[],"label_provenance":"tests/fixtures/reach-001.md","eligibility":"eligible","notes":"closed-world synthetic fixture"}
```
Field types: every *_id nonempty string; source ID must exist in source-lock or fixture registry; `project_relpath` relative and path traversal prohibited; `entry_points`/`target_symbols` are arrays of canonical FQNs; `expected_label` ∈ `reachable/unreachable/unknown/not_applicable`; `case_kind` ∈ `call_graph/reachability/integration/performance`; `expected_edges` is list of `[caller,callee]` pairs; `eligibility` ∈ `eligible/unsupported/blocked`; `notes`, `label_provenance` nonempty.

### Invariants
- `call_graph` requires `expected_label=not_applicable`; positive graph gold edges are from third-party reference, not PyReach predicted output.
- `reachability` requires ≥1 verified entry point and ≥1 target symbol except an `unknown` fixture deliberately testing missing mapping (which must carry explanatory provenance).
- `integration/performance` without independently verified graph ground truth uses `expected_label=not_applicable`; do not score it as a labeled negative.
- Fixture IDs and source IDs are stable; no duplicate PyCG-origin micro cases counted separately.

## Invalid example and error
`{"case_id":"reach-001","expected_label":"exploitable","project_relpath":"../../etc"}` → `SCHEMA_INVALID` (invalid label/path traversal, missing fields).

## Producer and consumer
Producers: S1/S2 dataset adapters and human fixture review. Consumers: runner and scorer. Error contracts: missing source → `SOURCE_UNAVAILABLE`; missing symbol provenance → `SYMBOL_UNVERIFIED`; not-applicable dataset type → `BENCHMARK_NOT_APPLICABLE`.
