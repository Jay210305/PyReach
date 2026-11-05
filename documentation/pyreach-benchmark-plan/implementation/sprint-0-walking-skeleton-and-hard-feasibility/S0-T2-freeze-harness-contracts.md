---
id: S0-T2
sprint: 0
owner: benchmark-agent
effort_h: 4
depends_on: [S0-T1]
status: done
---

# S0-T2 — Review contracts and initialize harness schemas

## Interface Contract
**Single sources of truth:** `docs/contracts/source-lock.md`, `docs/contracts/benchmark-case.md`, `docs/contracts/result-record.md`, `docs/contracts/report.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Acceptance Criteria (verbatim roadmap)
Create approved draft-compatible case/result JSON Schemas with 1 valid and 1 invalid fixture per boundary; `python3 scripts/validate_plan.py` exits 0.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then write failing acceptance/rejection contract tests including unknown labels and SHA-required completed records. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.2 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then create minimal schemas for case and result, shared error enums, untrusted source path traversal rejection. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.3 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then add source lock/report schema validation, fixture samples valid and invalid. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.4 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then run schema and plan lint, record contract decisions and any breaking changes in ADR. Demonstrate red→green or review evidence before completing this item.

## Verification (copy and paste from PyReach repo root)
```bash
python3 scripts/validate_plan.py && uv run --offline --no-sync pytest tests/unit -q
```
Result: `PLAN LINT OK` (after S0 harness files are finalized) and `452 passed, 1 skipped`.

## Definition of Done
- [x] S0-T1 audit recorded; dependency satisfied.
- [x] Contract boundary clarified; remaining schema work is gated to S1/T2 (planned, not created).
- [x] No invented source hashes, OSV DB schema, or graph export claims.
- [x] Not done: `benchmarks/pyreach_eval/...` artifacts are deliberately withheld (they are S1 targets).
