---
id: S3-T4
sprint: 3
owner: benchmark-agent
effort_h: 4
depends_on: [S1-T3, S2-T4, S3-T1]
status: todo
---
# S3-T4 — Measure package, graph and reachability baselines in separate scopes

| Sprint | Owner | Effort (h, sum to total) | Dependencies | Related docs |
|---|---|---:|---|---|
| 3 | benchmark-agent | 4 | S1-T3, S2-T4, S3-T1 | REQ-10, `03-technical-spec.md`, `06-ci-cd-environments.md` |

## Purpose
Measure package, graph and reachability baselines in separate scopes. Implements REQ-10; the outcome is an independently verifiable benchmark **artifact** and an honest evidence status, not an assumed scanner success.

## Preconditions / Definition of Ready
- [ ] Normal execution: explicit G0–G4 approval is required before task becomes Ready; check tracking/approval-gates.md.
- [ ] Dependency tasks S1-T3, S2-T4, S3-T1 merged with evidence; relevant QG-00 passes.
- [ ] The current PyReach checkout, OSV snapshot and sources actually exist locally where required; record commit/SHA and licenses. No invented external source paths.
- [ ] Contracts named below have at least proposed examples; formal approval follows the stated gate exception, if any; estimate 4 h accepted.

## Interface Contract
**Single sources of truth:** `docs/contracts/source-lock.md`, `docs/contracts/result-record.md`, `docs/contracts/report.md`.
- **Inputs:** locked source records/fixture case IDs and validated local paths as appropriate; production PyReach CLI is `uv run --offline --no-sync pyreach <project> --db-path <db> -o <sarif>`.
- **Outputs:** testable artifact paths listed below, case/run dispositions, hashes, stderr/exit and any validated SARIF or graph projection.
- **Errors:** `SCHEMA_INVALID`, `SOURCE_UNAVAILABLE`, `GRAPH_EXPORT_UNSUPPORTED`, `SYMBOL_UNVERIFIED`, `CLI_ERROR`, `TIMEOUT`, `LICENSE_RESTRICTED` as applicable; unsupported ≠ zero-score and scanner exit 1 ≠ failure.
- **Valid sample:** `{'case_id':'synthetic-001', 'run_status':'completed', 'scanner_exit_code':1, 'prediction':'reachable'}` is conceptually valid *only if all required provenance fields from C-RESULT are supplied*.
- **Invalid sample:** `scanner_exit_code=2` + `prediction=unreachable` + `run_status=completed` → `SCHEMA_INVALID`; do not score a runtime failure as a negative.

## Essential Sub-tasks (≤2 h each, test-first)
- [ ] 4.1 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then test first: reject metric join when package, graph or runtime reachability scopes differ. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.2 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then run cached package advisory detectors only where lock/version and DB snapshot equivalence can be established. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.3 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then run graph tools and VulnReach comparator where safe/eligible, otherwise document tool and environmental blockers. Demonstrate red→green or review evidence before completing this item.
- [ ] 4.4 (1 h) **Test/review first:** add or select a failing assertion/checklist specific to this unit; then report differences with normalization, inputs/DB coverage and no false statistical equivalence. Demonstrate red→green or review evidence before completing this item.

**Subtask total:** 1 + 1 + 1 + 1 = **4 h**.

## Deliverables
- `benchmarks/pyreach_eval/tests/test_baselines.py` — **future** exact target output; only report created when present.
- `benchmarks/reports/baselines/REPORT.md` — **future** exact target output; only report created when present.

## Acceptance Criteria (verbatim roadmap)
One per-category comparison for pip-audit, OSV-Scanner, PyCG/Pyan3, and VulnReach attempted when eligible; 0 cross-scope F1 equivalence claims.

## Verification (copy and paste from PyReach repo root)
```bash
uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests/test_baselines.py -q
```
Run relevant quality gates QG-00–QG-09 from `06-ci-cd-environments.md`. If this command cannot run because dependencies/corpus are not prepared, record a `blocked` or `unsupported` result; never report green CI. All changes must be linked to the current task's commit and an immutable result path.

## Edge Cases & Pitfalls
Never silently fetch latest advisory feeds during offline evaluation; VulnReach may require substantial services.

**Cross-cutting scope:** This is an evaluation task, not evidence of PyReach correctness. Use only pinned inputs and scanned source treated as data. During analysis do not access network; untrusted project code must not execute. Preserve `completed / unsupported / blocked / error` and `reachable / unreachable / unknown` separately. `uv run --offline --no-sync` requires a prepared environment; missing preparation is a blocker, not a pass.

## Risks / Scope Cuts
- Applicable risks and mitigations are enumerated in `07-risks.md` and the sprint's `04` mitigations section.
- **Cut policy:** Defer only Should/Could enhancement; preserve Must measurements and evidence.
- Source unavailable/licensed? Record `SOURCE_UNAVAILABLE` / `LICENSE_RESTRICTED` with evidence; no replacement scores or hidden denominator removal.

## Definition of Done
- [ ] Verifiable acceptance criterion met or transparently blocked with case-level reason.
- [ ] All subtask test/review-first checks complete; subtask hours sum to frontmatter effort.
- [ ] Contract valid/invalid samples tested and evidence hashes preserved.
- [ ] Relevant centralized QGs green (or unsupported reason explicitly approved).
- [ ] Write actual effort, artifacts and commit to `tracking/progress-log.md`; update task frontmatter status; 1 logical commit (`test(benchmark): S3-T4 ...`).
