---
id: S4-T4
sprint: 4
owner: benchmark-agent
effort_h: 4
depends_on: [S1-T3, S3-T3]
status: done
---

# S4-T4 — Close release and postmortem

## Purpose
Close release and postmortem. Implements REQ-13; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [x] Normal execution: explicit G0–G6 approval is recorded in `tracking/approval-gates.md`.
- [x] Dependency tasks S1-T3, S3-T3 merged with evidence; relevant QG-00 passes.
- [x] Current PyReach checkout audited; OSV SQLite schema confirmed in production (`pyreach/db/schema.sql`); no invented source paths.
- [x] Contracts named below have proposed boundaries; formal approval is stored in `tracking/approval-gates.md`.

## Windows platform constraint
- Host: Windows Git Bash; `python` -> `Python 3.14.7`.
- Do not use symlink-based fixtures (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/`chroot`; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1 audit confirmed: PyReach public CLI emits SARIF only; graph export unsupported by default.
- No release candidate, clean-install smoke, or postmortem evidence was produced because no corpus and no case harness were executed.

## Interface Contract
**Single sources of truth:** `docs/contracts/report.md`.
- **Inputs:** frozen case IDs, run records, scorer metrics.
- **Outputs:** release notes, cleanup of S-4 debt, explicit release approval record.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; unsupported != zero-score.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** release checker rejects unsigned/unhashed or missing Must evidence (blocked until corpus present).
- [ ] 4.2 (1 h) **Test/review first:** run plan linter and full centralized quality gates; reconcile roadmap vs task hours (blocked until corpus present).
- [ ] 4.3 (1 h) **Test/review first:** create changelog, proposed `bench-v0.1.0-rc.1`, clean install smoke proof and rollback directions (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** write estimate-vs-actual and gaps postmortem; migrate debt, request explicit release approval (blocked until corpus present).

Subtask total: 1 + 1 + 1 + 1 = **4 h**.

## Acceptance Criteria (verbatim roadmap)
Plan lint zero errors, Must checklist and QG statuses recorded, clean-install smoke documented, hours vs actual table published and remaining debt migrated; release remains pending without owner sign-off.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py && uv run --no-sync pytest tests/unit -q
```

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] Windows audit and S1-T2/S2-T3 evidence recorded; no fabricated release claims.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes or OSV DB schemas; production schema left untouched.
- [ ] Blocked: no corpus- or harness-derived release evidence exists to validate.
