---
id: S4-T1
sprint: 4
owner: benchmark-agent
effort_h: 5
depends_on: [S0-T3, S3-T3]
status: done
---

# S4-T1 — Validate SARIF v2.1.0, exit-code semantics and offline isolation

## Purpose
Validate SARIF v2.1.0, exit-code semantics and offline isolation. Implements REQ-11; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [x] Normal execution: explicit G0–G6 approval is recorded in `tracking/approval-gates.md`.
- [x] Dependency tasks S0-T3, S3-T3 merged with evidence; relevant QG-00 passes.
- [x] Current PyReach checkout audited; OSV SQLite schema confirmed in production (`pyreach/db/schema.sql`); no invented source paths.
- [x] Contracts named below have proposed boundaries; formal approval is stored in `tracking/approval-gates.md`.

## Windows platform constraint
- Host: Windows Git Bash; `python` -> `Python 3.14.7`.
- Do not use symlink-based fixtures (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/`chroot`; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1 audit confirmed: PyReach public CLI emits SARIF only; graph export unsupported by default.
- No SARIF file, exit-code control suite, or network-denied sandbox was executed in this environment.

## Interface Contract
**Single sources of truth:** `docs/contracts/cli-adapter.md`, `docs/contracts/result-record.md`, `docs/contracts/report.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED`; unsupported != zero-score, scanner exit 1 != failure.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** malformed SARIF, unknown exit and network-allowed setup are rejected (blocked until corpus present).
- [ ] 4.2 (1 h) **Test/review first:** validate JSON output against pinned official SARIF 2.1.0 schema and results data paths (blocked until corpus present).
- [ ] 4.3 (1 h) **Test/review first:** exercise real controlled exit 0/1/2 including `--no-fail` (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** run denied-network execution and capture proof, report enforcement/no-network failures (blocked until corpus present).
- [ ] 4.5 (1 h) **Test/review first:** verified SARIF on a 2-result SARIF v2.1.0 fixture with valid/invalid boundary (blocked until corpus present).

Subtask total: 1 + 1 + 1 + 1 + 1 = **5 h**.

## Acceptance Criteria (verbatim roadmap)
Eligible SARIF conforms to pinned v2.1.0 schema; 0,1,2 control cases pass; 0 network successes under enforced isolation, otherwise explicit blocked outcome.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py && uv run --no-sync pytest tests/unit -q
```

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] Windows audit and S1-T2/S2-T3 evidence recorded; no fabricated SARIF or exit-code claims.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes or OSV DB schemas; production schema left untouched.
- [ ] Blocked: SARIF schema version check, exit-code controls and network-denied sandbox require corpus/harness inputs not present.
