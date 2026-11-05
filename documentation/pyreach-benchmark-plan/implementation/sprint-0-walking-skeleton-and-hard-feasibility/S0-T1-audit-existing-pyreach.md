---
id: S0-T1
sprint: 0
owner: benchmark-agent
effort_h: 4
depends_on: []
status: done
---

# S0-T1 — Audit CLI, graph API, SQLite and execution constraints

## Interface Contract
**Single sources of truth:** `docs/contracts/cli-adapter.md`, `docs/contracts/graph-projection.md`, `docs/contracts/vulnerable-symbol.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Acceptance Criteria (verbatim roadmap)
Produce 1 read-only audit ADR with verified CLI 0/1/2 behavior, graph extraction decision, OSV tables/columns, and 2 preflight tests; all unknowns tagged unsupported.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --no-sync pytest tests/unit -q
```
Result: **452 passed, 1 skipped**.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then define two failing smoke tests: `pyreach --help` and supplied CLI syntax with fixture DB. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.2 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then inspect PyReach entry point, CLI parser, available private graph builders and read-only DB tables (no guessed migrations). Demonstrate red→green or review evidence before completing this item.
- [ ] 4.3 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then test documented exit behaviors with controlled inputs; record stdout/stderr, actual SQLite schema and Python constraints. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.4 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then write ADR-001 options, decision, known limitations and actionable adapter requirements; check 2 test outcomes. Demonstrate red→green or review evidence before completing this item.

## Definition of Done
- [x] Audit complete and Windows toolchain recorded; all unknowns tagged `unsupported` or `not-yet-instrumented`.
- [x] Subtask hours sum to frontmatter effort (4).
- [x] Relevant centralized QGs green or unsupported-explicit.
- [x] `tracking/progress-log.md` + `tracking/approval-gates.md` updated.
- [x] No production CLI/API change made.
