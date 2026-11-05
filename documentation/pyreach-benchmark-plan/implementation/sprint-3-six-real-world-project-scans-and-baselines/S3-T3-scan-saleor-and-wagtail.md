---
id: S3-T3
sprint: 3
owner: benchmark-agent
effort_h: 6
depends_on: [S2-T4, S2-T3]
status: done
---

# S3-T3 — Stress-test Saleor and Wagtail with resource limits

## Purpose
Stress-test Saleor and Wagtail with resource limits. Implements REQ-09; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [x] Normal execution: explicit G0–G6 approval is recorded in `tracking/approval-gates.md`.
- [x] Dependency tasks S2-T4, S2-T3 merged with evidence; relevant QG-00 passes.
- [x] Current PyReach checkout audited; OSV SQLite schema confirmed in production (`pyreach/db/schema.sql`); no invented source paths.
- [x] Contracts named below have proposed boundaries; formal approval is stored in `tracking/approval-gates.md`.

## Windows platform constraint
- Host: Windows Git Bash; `python` -> `Python 3.14.7`.
- Do not use symlink-based fixtures (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/`chroot`; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- S1 audit confirmed: PyReach public CLI emits SARIF only; graph export unsupported by default.
- The six project roots are **not local**. Seeded Time/Memory caps are recorded, but no run was executed.

## Interface Contract
**Single sources of truth:** `docs/contracts/benchmark-case.md`, `docs/contracts/source-lock.md`.
- **Inputs:** pinned source commits for `saleor/saleor` and `wagtail/wagtail`.
- **Outputs:** run records with sparse/root manifest, file count and LOC, Time/Memory cap, SARIF/exit capture, and TIMEOUT/RESOURCE_LIMIT classification.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; blocked != unsupported, unsupported != negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** a large repo with no seeded Time/Memory cap becomes TIMEOUT/RESOURCE_LIMIT. (oracle)
- [ ] 4.2 (2 h) **Test/review first:** identify Saleor `pyproject.toml` + `uv.lock` roots and sparse file count (blocked until corpus present).
- [ ] 4.3 (2 h) **Test/review first:** identify Wagtail `pyproject.toml` + `uv.lock` root and Python dynamic packaging (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** write two run records and a resource cap proof (blocked until corpus present).

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
2 large repos pinned with env/LOC/file counts and scan outcomes, timeout 900s and RSS cap 8GiB or documented approved adjustment; never hide errors.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py && uv run --no-sync pytest tests/unit -q
```

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] Windows audit and S1-T2/S2-T3 evidence recorded; no fabricated project scan outputs.
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes or OSV DB schemas; production schema left untouched.
- [ ] Blocked: project roots, manifests, and OSV snapshot not acquired locally.
