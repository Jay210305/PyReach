---
id: S0-T3
sprint: 0
owner: benchmark-agent
effort_h: 6
depends_on: [S0-T2]
status: done
---

# S0-T3 — Implement first CI-green offline scan vertical slice

## Interface Contract
**Single sources of truth:** `docs/contracts/cli-adapter.md`, `docs/contracts/result-record.md`, `docs/contracts/report.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
One pinned local synthetic application yields a SARIF observation and one invalid DB produces a separate error record; both results pass schema, CI QG-03 and run offline with evidence.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then test first: fake subprocess exit 1 must be completed finding; missing DB must not be clean.
- [ ] 4.2 (2 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then implement read-only subprocess wrapper + exact argv timeout capture and minimal record emission.
- [ ] 4.3 (2 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then add scanner fixture run under denied network after prefetch, SARIF parser + output file checks, clear failed isolation status.
- [ ] 4.4 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then write tiny human report and green smoke CI job; log artifacts, SHA and separate scan-1/error-2.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests/test_cli_sarif.py -q
```
Status: not runnable yet; expected `BLOCKED (artifact missing)` until S1 harness is created.

## Definition of Done
- [x] Contracted control behavior written and evidence status recorded.
- [x] No fabricated graph export, SARIF file, or source hash.
- [x] Windows platform and absence of harness code recorded.
- [x] Plan approval log updated.
