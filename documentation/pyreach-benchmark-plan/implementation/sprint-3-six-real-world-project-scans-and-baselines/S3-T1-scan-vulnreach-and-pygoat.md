---
id: S3-T1
sprint: 3
owner: benchmark-agent
effort_h: 6
depends_on: [S2-T4, S2-T3]
status: done
---

# S3-T1 — Scan VulnReach and PyGoat under isolation

## Purpose
Scan VulnReach Python lab and PyGoat under isolation. Implements REQ-09; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

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
- The six project roots are **not local**; the 36-case corpus is **not local**. No VCS fetch, manifest resolution, or scan output is available to record.

## Interface Contract
**Single sources of truth:** `docs/contracts/benchmark-case.md`, `docs/contracts/source-lock.md`.
- **Inputs:** pinned source commits and manifests for `OWASP/VulnReach` and `adeyosemanputra/pygoat`.
- **Outputs:** run record with manifest root, snapshot hash, SARIF/exit capture, and explicit ground-truth limitations.
- **Errors:** `SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `CLI_ERROR`, `TIMEOUT`, `RESOURCE_LIMIT`; blocked != unsupported, unsupported != negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** a project root without manifest produces blocked not clean; no startup hooks (oracle).
- [ ] 4.2 (2 h) **Test/review first:** identify VulnReach `labs/python_vuln_app` manifest root and static scan behavior (blocked until corpus present).
- [ ] 4.3 (2 h) **Test/review first:** identify PyGoat Django manifest and Python constraints; static-only classification (blocked until corpus present).
- [ ] 4.4 (1 h) **Test/review first:** write two run records and a ground-truth limitations note (blocked until corpus present).

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
2 pinned project roots with manifest path, snapshot hash, SARIF/exit capture and explicit ground-truth limitations; completed or documented blocked.

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
