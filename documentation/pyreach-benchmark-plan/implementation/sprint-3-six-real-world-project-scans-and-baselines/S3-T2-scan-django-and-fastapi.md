---
id: S3-T2
sprint: 3
owner: benchmark-agent
effort_h: 6
depends_on: [S2-T4, S2-T3]
status: done
---

# S3-T2 — Scan Django RealWorld and FastAPI template

## Purpose
Scan Django RealWorld and FastAPI backend template. Implements REQ-09; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

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
- The six project roots are **not local**. Static-only scanning of Django RealWorld is documented as the safe mode; no CLI run output exists to record.

## Interface Contract
**Single sources of truth:** `docs/contracts/benchmark-case.md`, `docs/contracts/source-lock.md`.
- **Inputs:** pinned source commits for `gothinkster/django-realworld-example-app` and `fastapi/full-stack-fastapi-template`.
- **Outputs:** run records with manifest roots (RealWorld `requirements.txt`; FastAPI `backend/pyproject.toml` + root `uv.lock`), snapshot hash, SARIF/exit capture, and explicit ground-truth limitations.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; blocked != unsupported, unsupported != negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** source root != lock root handled explicitly; legacy app imports forbidden (oracle).
- [ ] 4.2 (2 h) **Test/review first:** identify Django RealWorld `requirements.txt` and archived Python constraints; static scan only (blocked until corpus present).
- [ ] 4.3 (2 h) **Test/review first:** identify FastAPI template `backend/pyproject.toml` and root `uv.lock` workspace behavior; scan supported roots (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** write two run records and a ground-truth limitations note (blocked until corpus present).

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
2 additional pinned project roots scanned or blocked; FastAPI workspace lock root and backend source root documented separately; archived Django requires no app execution.

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
