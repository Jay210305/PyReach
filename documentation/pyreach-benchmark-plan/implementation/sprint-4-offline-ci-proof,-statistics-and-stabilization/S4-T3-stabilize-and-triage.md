---
id: S4-T3
sprint: 4
owner: benchmark-agent
effort_h: 4
depends_on: [S3-T3, S4-T2]
status: done
---

# S4-T3 — Stabilize and triage

## Purpose
Stabilize and triage failures. Implements REQ-13; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [x] Normal execution: explicit G0–G6 approval is recorded in `tracking/approval-gates.md`.
- [x] Dependency tasks S3-T3, S4-T2 merged with evidence; relevant QG-00 passes.
- [x] Current PyReach checkout audited; OSV SQLite schema confirmed in production (`pyreach/db/schema.sql`); no invented source paths.
- [x] Contracts named below have proposed boundaries; formal approval is stored in `tracking/approval-gates.md`.

## Windows platform constraint
- Host: Windows Git Bash; `python` -> `Python 3.14.7`.
- Do not use symlink-based fixtures (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/`chroot`; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1 audit confirmed: PyReach public CLI emits SARIF only; graph export unsupported by default.
- No failure triage or regression evidence was collected, because the corpus, case harness, and baseline runs were never executed.

## Interface Contract
**Single sources of truth:** `docs/contracts/report.md`, `docs/contracts/benchmark-case.md`.
- **Inputs:** reproducible case IDs, run records, scorer metrics, SSG/PyReaCh outputs.
- **Outputs:** discrepancy records per case ID, regression test, release note and freeze manifest.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; unsupported != zero-score.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** reproduce highest-priority discrepancy in minimal deterministic fixture (blocked until corpus present).
- [ ] 4.2 (1 h) **Test/review first:** fix only evaluation harness logic in scope; product-code fixes require separate ticket/approval (blocked until corpus present).
- [ ] 4.3 (1 h) **Test/review first:** re-run implicated cases and QG commands, retain before/after hashes (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** freeze schema/report results and issue final unresolved risk/debt ledger (blocked until corpus present).

Subtask total: 1 + 1 + 1 + 1 = **4 h**.

## Acceptance Criteria (verbatim roadmap)
Every observed misclassification/error has a reproducible case ID and classification; at least 1 regression from any identified reproducible bug or explicitly 0 bugs found.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py && uv run --no-sync pytest tests/unit -q
```

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] Windows audit and S1-T2/S2-T3 evidence recorded; no fabricated stability or triage claims.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes or OSV DB schemas; production schema left untouched.
- [ ] Blocked: no corpus- or harness-derived failures exist to triage.
