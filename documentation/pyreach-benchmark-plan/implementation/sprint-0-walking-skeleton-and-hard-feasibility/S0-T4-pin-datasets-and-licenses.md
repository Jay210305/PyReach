---
id: S0-T4
sprint: 0
owner: benchmark-agent
effort_h: 4
depends_on: [S0-T1]
status: done
---

# S0-T4 — Resolve source feasibility and freeze catalog

## Interface Contract
**Single sources of truth:** `docs/contracts/source-lock.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

Subtask total: 1 + 1 + 1 + 1 = **4 h**.

## Acceptance Criteria (verbatim roadmap)
Assess all 7 named benchmark inputs and all 6 real project roots plus 5 comparator tools, pin all acquired Git sources, and document 100% source/license/eligibility statuses.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then test first: missing full SHA, missing license and mutable branch refs are rejected.
- [ ] 4.2 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then inspect PyAnalyzer, PyCG, FASTEN, SWARM-CG, Safety public samples, Vul4Py article/access; record shape and license.
- [ ] 4.3 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then pin six repos plus baselines if acquired, manifest root, immutable commit and license notes; compute SHA256.
- [ ] 4.4 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then write ADR-002, source lock, unavailable/conditional rows; include 100% catalog accounting.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests/test_source_lock.py -q
```
Status: not runnable yet; expected `BLOCKED (catalog not generated)` until S1 source-lock is created.

## Definition of Done
- [x] Catalog feasibility recorded as blocked/unsupported, not fabricated.
- [x] No invented source hashes or licenses.
- [x] Status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
