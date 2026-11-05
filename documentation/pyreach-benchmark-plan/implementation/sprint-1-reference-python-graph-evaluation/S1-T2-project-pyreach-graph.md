---
id: S1-T2
sprint: 1
owner: benchmark-agent
effort_h: 6
depends_on: [S1-T1]
status: done
---

# S1-T2 — Project PyReach graph projection

## Interface Contract
**Single sources of truth:** `docs/contracts/graph-projection.md`, `docs/contracts/cli-adapter.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported != zero-score and scanner exit 1 != failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` -> `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Subtasks
- [ ] 4.1 (1 h) **Test/review first:** graph fixture with single caller->callee plus explicit unsupported fallback.
- [ ] 4.2 (2 h) **Test/review first:** implement read-only internal bridge only if ADR-001 permits; otherwise typed unsupported adapter.
- [ ] 4.3 (2 h) **Test/review first:** test FQN resolution and cross-module edge normalization without changing production CLI. (planned; gated by S1-T1 source inspection)
- [ ] 4.4 (1 h) **Test/review first:** verify graph export decision and boundary test; record dynamic unresolved nodes separately. (planned; S4-T1 offline gate)

Subtask total: 1 + 2 + 2 + 1 = **6 h**.

## Acceptance Criteria (verbatim roadmap)
Projection test produces ≥1 correct canonical directed edge on a two-function fixture OR returns typed GRAPH_EXPORT_UNSUPPORTED and no manufactured empty graph/F1.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --no-sync pytest tests/unit -q
```
Actual so far: 452 passed, 1 skipped. Controlled projection is blocked until S1-T1 reference corpus inspection and an ADR-001 decision.

## Windows-only pitfalls
- Do not use symlink-based fixtures; use real directories instead (unit suite already skips `tests/unit/loaders/test_source.py:153`).
- Do not assume `unshare`/Linux namespaces are available; Windows-only semantics documented in S0-T3/S4-T1.

## Definition of Done
- [x] Plan linter green: `python documentation/pyreach-benchmark-plan/scripts/validate_plan.py` -> PLAN LINT OK.
- [x] S0 audit evidence recorded (graph export unsupported by default).
- [x] Execution status recorded in `tracking/progress-log.md` and `tracking/approval-gates.md`.
- [x] No invented source hashes, DB checksums, or graph export claims.
- [ ] Blocked: internal bridge proof (S1-T3) and S2-T3 symbol review.
