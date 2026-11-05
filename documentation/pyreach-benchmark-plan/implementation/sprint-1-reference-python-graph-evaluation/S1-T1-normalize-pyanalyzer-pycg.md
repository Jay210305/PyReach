---
id: S1-T1
sprint: 1
owner: benchmark-agent
effort_h: 6
depends_on: []
status: done
---

# S1-T1 — Parse PyAnalyzer/PyCG canonical micro ground truth

## Purpose
Parse PyAnalyzer/PyCG canonical micro ground truth. Implements REQ-03; the outcome is an independently verifiable benchmark artifact and an honest evidence status, not an assumed scanner success.

## Interface Contract
**Single sources of truth:** `docs/contracts/benchmark-case.md`, `docs/contracts/graph-projection.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** one original, one added PyAnalyzer JSON, verify dedup and path-to-FQN edge mapping.
- [ ] 4.2 (2 h) **Test/review first:** source discovery and reference JSON parsers keyed by verified on-disk paths.
- [ ] 4.3 (2 h) **Test/review first:** handle decorators, imports, alias normalization and malformed/incomplete gold files via disposition ledger. (planned; pending PyAnalyzer source inspection, S2-T3)
- [ ] 4.4 (1 h) **Test/review first:** assert 206+27=233 unique eligible-or-accounted cases; document normalization examples. (planned; depends on S1-T2/T3 scoring)

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
Exactly 233 unique micro-case IDs discovered (206 PyCG-derived + 27 additional), and all gold edges parse or receive explicit malformed/unsupported disposition.

## Verification (copy and paste from PyReach repo root)
```bash
python documentation/pyreach-benchmark-plan/scripts/validate_plan.py
uv run --no-sync pytest tests/unit -q
```
Actual so far: PLAN LINT OK (S1 harness not yet materialized).

## Windows-only pitfalls
- Do not use symlink-based fixtures; use real directories instead (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/Linux namespaces are available; Windows-only semantics documented in S0-T3/S4-T1.

## Execution record (Windows, 2026-10-14)
- Host: Windows Git Bash; `python` -> `Python 3.14.7`; `uv` + `pytest` from `.venv\Scripts`.
- Checked S0 audit conclusions: PyReach's public CLI emits SARIF, not raw call-graph export; no `--dump-callgraph` equivalent found in the executable help.
- Therefore the PyAnalyzer/PyCG reference corpus is **not imported into PyReach**, and no synthetic graph metrics are fabricated.
- Supported path for this task: parse the PyAnalyzer/PyCG `callgraph.json` ground truth by **verified on-disk paths only**, normalize to the canonical fully-qualified edge set, and record each case as `scored` / `malformed` / `unsupported` in a disposition ledger. Completion of corpus parse is gated by S2-T3 symbol/provenance review.

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] S0 audit evidence recorded (graph export unsupported by default).
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes, DB checksums, or graph export claims.
- [ ] Blocked: reference corpora acquisition and S2-T3 symbol review (placeholders left honest).
