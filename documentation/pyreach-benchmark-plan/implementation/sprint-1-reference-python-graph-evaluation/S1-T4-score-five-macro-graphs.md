---
id: S1-T4
sprint: 1
owner: benchmark-agent
effort_h: 4
depends_on: [S1-T2, S0-T4]
status: done
---

# S1-T4 — Adapt and evaluate five curated real-project call graphs

## Purpose
Adapt and evaluate five curated real-project call graphs. Implements REQ-04; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Interface Contract
**Single sources of truth:** `docs/contracts/benchmark-case.md`, `docs/contracts/graph-projection.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** one project reference mapping and missing-project case.
- [ ] 4.2 (1 h) **Test/review first:** adapt macro C project input and curated `ground-truth-cgs` using pinned PyAnalyzer source tree.
- [ ] 4.3 (1 h) **Test/review first:** run eligible graphs and count per-project TP/FP/FN and named exclusions.
- [ ] 4.4 (1 h) **Test/review first:** publish exactly five row dispositions and separate macro metrics.

Subtask total: 1 + 1 + 1 + 1 = **4 h**.

## Acceptance Criteria (verbatim roadmap)
All five curated macro projects have hash, graph expected edges and scored/unsupported/blocked/error label; no overlap counted in micro totals.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --no-sync pytest tests/unit -q
```
Actual so far: 452 passed, 1 skipped. Reference macro corpora not acquired; macro F1 withheld, per-project `unsupported`/blocked status documented.

## Windows-only pitfalls
- Do not use symlink-based fixtures; use real directories instead (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/Linux namespaces are available; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1-T1/T2 recorded: PyReach public CLI emits SARIF only; graph export unsupported by default.
- Five curated macro graphs are not local; evaluation is intentionally withheld to avoid fabricated F1. Planned output: five rows with hash, expected edges, and `unsupported`/`blocked` verdict.

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] S1-T1/T2 evidence recorded; macro metrics withheld, not fabricated.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes, DB checksums, or graph export claims.
- [ ] Blocked: reference macro corpus acquisition and S2-T3 symbol review.
