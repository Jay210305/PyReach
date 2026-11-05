---
id: S4-T2
sprint: 4
owner: benchmark-agent
effort_h: 5
depends_on: [S1-T3, S2-T4]
status: done
---

# S4-T2 — Generate reproducible accuracy and performance reports

## Purpose
Generate reproducible accuracy and performance reports. Implements REQ-12; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [x] Normal execution: explicit G0–G6 approval is recorded in `tracking/approval-gates.md`.
- [x] Dependency tasks S1-T3, S2-T4 merged with evidence; relevant QG-00 passes.
- [x] Current PyReach checkout audited; OSV SQLite schema confirmed in production (`pyreach/db/schema.sql`); no invented source paths.
- [x] Contracts named below have proposed boundaries; formal approval is stored in `tracking/approval-gates.md`.

## Windows platform constraint
- Host: Windows Git Bash; `python` -> `Python 3.14.7`.
- Do not use symlink-based fixtures (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/`chroot`; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1 audit confirmed: PyReach public CLI emits SARIF only; graph export unsupported by default.
- No case-level JSONL, summary, or timing evidence exists because the corpora and 36-case harness were not created. The release report is an explicit `blocked` record.

## Interface Contract
**Single sources of truth:** `docs/contracts/result-record.md`, `docs/contracts/report.md`.
- **Inputs:** case-level JSONL, run-config, source manifest, run records, scorer metrics.
- **Outputs:** `benchmarks/reports/YYYYMMDD-runid/` artifacts: run-config.json, source-manifest.json, case-results.jsonl, summary.json, summary.csv, per-project findings/*.sarif, process/*.json.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; unsupported != zero-score.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** confusion matrix mismatch, missing hashes and mixed baseline denominators rejected (blocked until corpus present).
- [ ] 4.2 (2 h) **Test/review first:** aggregate separate callgraph/symbol reachability metrics, predicted unknown and unsupported (blocked until corpus present).
- [ ] 4.3 (1 h) **Test/review first:** execute 3 warm repeat runs per eligible six project roots within caps; record censored runs/timeouts (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** generate JSON/CSV/Markdown reports and per-project performance evidence; verify sums (blocked until corpus present).

Subtask total: 1 + 2 + 1 + 1 = **5 h**.

## Acceptance Criteria (verbatim roadmap)
Report denominators, P/R/F1, 3 repeat runs per eligible project with median/p95/RSS, source/DB/tool hashes; zero simulated values marked real.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py && uv run --no-sync pytest tests/unit -q
```

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] Windows audit and S1-T2/S2-T3 evidence recorded; no fabricated performance or accuracy claims.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes or OSV DB schemas; production schema left untouched.
- [ ] Blocked: case-level JSONL, summary JSON/CSV and timing evidence require the 36-case harness, which is not present.
