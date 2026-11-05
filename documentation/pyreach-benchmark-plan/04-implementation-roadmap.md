# 04 — Implementation roadmap, capacity, critical path and cuts

**Plan status:** draft, not approved. **Owner:** `benchmark-agent` for each sprint. **Schedule:** five consecutive 2-week sprints (10 calendar weeks), dates set only after G0 approval. This is a relative sequence, not an invented start/end date.

## Cross-sprint scope and DoR
Must scope: all 233 unique micro and 5 curated macro inventories; FASTEN micro/Fabric; SWARM-CG eligibility; symbol/OSV+Safety public sample review; Vul4Py paper+assets eligibility; 36 labeled reachability fixtures; six real project roots; baselines; valid SARIF/exit/offline and evidence report. A dataset may be **blocked/unsupported** without losing accounting: it must not be scored as a pass or a failure. `Definition of Ready`: dependencies merged, input source/licensing pinned, contract reviewed, two test-first artifacts planned, estimate ≤8h, owner authorized.

## Sprint 0: Walking skeleton and hard feasibility (weeks 1–2)
**Duration:** 2 weeks | **Effort:** 18 h | **Status:** ⬜ | **Owner:** benchmark-agent
**Goal:** Audit real PyReach, freeze contract intent, deliver a single end-to-end offline scan recording SARIF/exit without invented graph support.

### Deliverables
1. CLI/DB/graph audit ADR and verified public-CLI smoke tests.
2. JSON schema contracts and one source-lock feasibility ADR.
3. An executable first vertical slice from input fixture → CLI → SARIF/exit → report.

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|---|---|---:|---|---|---|
| S0-T1 | Audit CLI, graph API, SQLite and execution constraints | 4 | benchmark-agent | ⬜ | Produce 1 read-only audit ADR with verified CLI 0/1/2 behavior, graph extraction decision, OSV tables/columns, and 2 preflight tests; all unknowns tagged unsupported. |
| S0-T2 | Review contracts and initialize harness schemas | 4 | benchmark-agent | ⬜ | Create approved draft-compatible case/result JSON Schemas with 1 valid and 1 invalid fixture per boundary; `python3 scripts/validate_plan.py` exits 0. |
| S0-T3 | Implement first CI-green offline scan vertical slice | 6 | benchmark-agent | ⬜ | One pinned local synthetic application yields a SARIF observation and one invalid DB produces a separate error record; both results pass schema, CI QG-03 and run offline with evidence. |
| S0-T4 | Resolve source feasibility and freeze catalog | 4 | benchmark-agent | ⬜ | Assess all 7 named benchmark inputs and all 6 real project roots plus 5 comparator tools, pin all acquired Git sources, and document 100% source/license/eligibility statuses. |

### DoD
- [ ] QG-00 plan lint green; all relevant QGs from `06-ci-cd-environments.md` run and their actual status recorded (do not claim unimplemented/unsupported gate passed).
- [ ] Contract tests and changed harness tests pass; harness code coverage ≥85% when coverage tooling configured.
- [ ] Source/data/repo hashes, issue status, and evidence paths saved; reports/ADRs updated.

### Mitigations
- R1/R2/R3 → S0-T1, R5 → S0-T4, R8 → S0-T3.


## Sprint 1: Reference Python graph evaluation (weeks 3–4)
**Duration:** 2 weeks | **Effort:** 22 h | **Status:** ⬜ | **Owner:** benchmark-agent
**Goal:** Normalize reference graph corpora, measure PyAnalyzer/PyCG, curated macros, and account for SWARM-CG.

### Deliverables
1. `benchmarks/pyreach_eval/adapters/pyanalyzer.py, benchmarks/pyreach_eval/tests/test_graph_cases.py` and reviewed evidence.
2. `benchmarks/pyreach_eval/graph/pyreach_bridge.py, benchmarks/pyreach_eval/tests/test_graph_bridge.py` and reviewed evidence.
3. `benchmarks/pyreach_eval/scoring/graph_metrics.py, benchmarks/reports/pyanalyzer-micro/REPORT.md` and reviewed evidence.
4. `benchmarks/pyreach_eval/adapters/pycg_macro.py, benchmarks/pyreach_eval/tests/test_macro.py` and reviewed evidence.
5. `benchmarks/pyreach_eval/adapters/swarmcg.py, benchmarks/pyreach_eval/tests/test_swarm.py` and reviewed evidence.

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|---|---|---:|---|---|---|
| S1-T1 | Parse PyAnalyzer/PyCG canonical micro ground truth | 6 | benchmark-agent | ⬜ | Exactly 233 unique micro-case IDs discovered (206 PyCG-derived + 27 additional), and all gold edges parse or receive explicit malformed/unsupported disposition. |
| S1-T2 | Expose auditable optional PyReach graph projection | 6 | benchmark-agent | ⬜ | Projection test produces ≥1 correct canonical directed edge on a two-function fixture OR returns typed GRAPH_EXPORT_UNSUPPORTED and no manufactured empty graph/F1. |
| S1-T3 | Execute 233 micro graph comparisons with denominator ledger | 4 | benchmark-agent | ⬜ | All 233 unique cases have scored/unsupported/blocked/error disposition; eligible graph totals and P/R/F1 reconcile exactly. |
| S1-T4 | Adapt and evaluate five curated real-project call graphs | 4 | benchmark-agent | ⬜ | All five curated macro projects have hash, graph expected edges and scored/unsupported/blocked/error label; no overlap counted in micro totals. |
| S1-T5 | Assess SWARM-CG Python fixtures and score unique subset | 2 | benchmark-agent | ⬜ | One Python SWARM-CG eligibility ledger documents all discovered cases, duplicates, scored/blocked status, with zero PyAnalyzer overlap in aggregates. |

### DoD
- [ ] QG-00 plan lint green; all relevant QGs from `06-ci-cd-environments.md` run and their actual status recorded (do not claim unimplemented/unsupported gate passed).
- [ ] Contract tests and changed harness tests pass; harness code coverage ≥85% when coverage tooling configured.
- [ ] Source/data/repo hashes, issue status, and evidence paths saved; reports/ADRs updated.

### Mitigations
- R1 → S1-T2; R4 → S1-T1 and S1-T5.


## Sprint 2: Cross-package and vulnerability truth (weeks 5–6)
**Duration:** 2 weeks | **Effort:** 22 h | **Status:** ⬜ | **Owner:** benchmark-agent
**Goal:** Evaluate FASTEN cross-package references and create audited vulnerable-symbol + 36-case reachability fixtures.

### Deliverables
1. `benchmarks/pyreach_eval/adapters/fasten.py, benchmarks/pyreach_eval/tests/test_fasten.py` and reviewed evidence.
2. `benchmarks/pyreach_eval/tests/test_fasten.py, benchmarks/reports/fasten-fabric/REPORT.md` and reviewed evidence.
3. `benchmarks/pyreach_eval/cases/vulnerable_symbols.jsonl, benchmarks/pyreach_eval/tests/test_symbols.py` and reviewed evidence.
4. `benchmarks/pyreach_eval/fixtures/, benchmarks/pyreach_eval/tests/test_reachability.py` and reviewed evidence.
5. `benchmarks/pyreach_eval/tests/test_vul4py.py, benchmarks/reports/vul4py-eligibility.md` and reviewed evidence.

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|---|---|---:|---|---|---|
| S2-T1 | Validate FASTEN cross-package micro graph stitching | 5 | benchmark-agent | ⬜ | All five micro packages (root, dep1, dep2, trans-dep1, trans-dep2) inventoried; cross-package gold/prediction edges scored or declared unsupported. |
| S2-T2 | Validate Fabric cross-package macro reference | 5 | benchmark-agent | ⬜ | Fabric macro expected stitched graph checksum and dependency list recorded; one scored/unsupported/blocked macro disposition with reason and edge accounting. |
| S2-T3 | Curate advisory-to-symbol provenance and DB fixture bridge | 5 | benchmark-agent | ⬜ | At least 1 reviewed synthetic symbol mapping and a provenance/eligibility row for each considered public Safety Python sample; zero verified symbols without evidence. |
| S2-T4 | Implement 36 reviewed controlled reachability scenarios | 5 | benchmark-agent | ⬜ | Exactly 12 reachable + 12 unreachable + 12 unknown *ground-truth* fixtures reviewed, each runnable/unsupported with stored outcome; zero negative labels lacking closed-world rationale. |
| S2-T5 | Evaluate Vul4Py transferability without oracle confusion | 2 | benchmark-agent | ⬜ | 100-vulnerability/60-project study described accurately, asset availability checked, and zero repair-oracle labels counted as reachability truth without reviewed symbol mapping. |

### DoD
- [ ] QG-00 plan lint green; all relevant QGs from `06-ci-cd-environments.md` run and their actual status recorded (do not claim unimplemented/unsupported gate passed).
- [ ] Contract tests and changed harness tests pass; harness code coverage ≥85% when coverage tooling configured.
- [ ] Source/data/repo hashes, issue status, and evidence paths saved; reports/ADRs updated.

### Mitigations
- R2/R11 → S2-T3 and S2-T4; R5 → S2-T5.


## Sprint 3: Six real-world project scans and baselines (weeks 7–8)
**Duration:** 2 weeks | **Effort:** 22 h | **Status:** ⬜ | **Owner:** benchmark-agent
**Goal:** Run three progressively harder pinned project cohorts and valid-scope baseline comparisons.

### Deliverables
1. `benchmarks/pyreach_eval/tests/test_project_catalog.py, benchmarks/reports/project-vulnreach/REPORT.md` and reviewed evidence.
2. `benchmarks/reports/project-django-realworld/REPORT.md, benchmarks/reports/project-fastapi/REPORT.md` and reviewed evidence.
3. `benchmarks/reports/project-saleor/REPORT.md, benchmarks/reports/project-wagtail/REPORT.md` and reviewed evidence.
4. `benchmarks/pyreach_eval/tests/test_baselines.py, benchmarks/reports/baselines/REPORT.md` and reviewed evidence.

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|---|---|---:|---|---|---|
| S3-T1 | Scan VulnReach Python lab and PyGoat under isolation | 6 | benchmark-agent | ⬜ | 2 pinned project roots with manifest path, snapshot hash, SARIF/exit capture and explicit ground-truth limitations; completed or documented blocked. |
| S3-T2 | Scan Django RealWorld and FastAPI backend workspace | 6 | benchmark-agent | ⬜ | 2 additional pinned project roots scanned or blocked; FastAPI workspace lock root and backend source root documented separately; archived Django requires no app execution. |
| S3-T3 | Stress-test Saleor and Wagtail with resource limits | 6 | benchmark-agent | ⬜ | 2 large repos pinned with env/LOC/file counts and scan outcomes, timeout 900s and RSS cap 8GiB or documented approved adjustment; never hide errors. |
| S3-T4 | Measure package, graph and reachability baselines in separate scopes | 4 | benchmark-agent | ⬜ | One per-category comparison for pip-audit, OSV-Scanner, PyCG/Pyan3, and VulnReach attempted when eligible; 0 cross-scope F1 equivalence claims. |

### DoD
- [ ] QG-00 plan lint green; all relevant QGs from `06-ci-cd-environments.md` run and their actual status recorded (do not claim unimplemented/unsupported gate passed).
- [ ] Contract tests and changed harness tests pass; harness code coverage ≥85% when coverage tooling configured.
- [ ] Source/data/repo hashes, issue status, and evidence paths saved; reports/ADRs updated.

### Mitigations
- R6 → S3-T2; R7/R9 → S3-T3; R10 → S3-T4.


## Sprint 4: Offline/CI proof, statistics and stabilization (weeks 9–10)
**Duration:** 2 weeks | **Effort:** 18 h | **Status:** ⬜ | **Owner:** benchmark-agent
**Goal:** Validate SARIF/exit codes/offline, repeat performance runs, triage discrepancies and create a release-ready evidence bundle.

### Deliverables
1. `benchmarks/pyreach_eval/tests/test_cli_sarif.py, benchmarks/reports/release/ci-offline-evidence.md` and reviewed evidence.
2. `benchmarks/pyreach_eval/scoring/metrics.py, benchmarks/pyreach_eval/tests/test_report.py` and reviewed evidence.
3. `benchmarks/reports/release/discrepancies.md, benchmarks/pyreach_eval/tests/test_regressions.py` and reviewed evidence.
4. `benchmarks/reports/release/CHANGELOG.md, benchmarks/reports/release/release-checklist.md` and reviewed evidence.

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|---|---|---:|---|---|---|
| S4-T1 | Validate SARIF v2.1.0, exit-code semantics and offline isolation | 5 | benchmark-agent | ⬜ | Eligible SARIF conforms to pinned v2.1.0 schema; 0,1,2 control cases pass; 0 network successes under enforced isolation, otherwise explicit blocked outcome. |
| S4-T2 | Generate reproducible accuracy and performance reports | 5 | benchmark-agent | ⬜ | Report denominators, P/R/F1, 3 repeat runs per eligible project with median/p95/RSS, source/DB/tool hashes; zero simulated values marked real. |
| S4-T3 | Triage failures, fix benchmark harness bugs, freeze evidence | 4 | benchmark-agent | ⬜ | Every observed misclassification/error has a reproducible case ID and classification; at least 1 regression from any identified reproducible bug or explicitly 0 bugs found. |
| S4-T4 | Validate plan, release smoke and postmortem | 4 | benchmark-agent | ⬜ | Plan lint zero errors, Must checklist and QG statuses recorded, clean-install smoke documented, hours vs actual table published and remaining debt migrated; release remains pending without owner sign-off. |

### DoD
- [ ] QG-00 plan lint green; all relevant QGs from `06-ci-cd-environments.md` run and their actual status recorded (do not claim unimplemented/unsupported gate passed).
- [ ] Contract tests and changed harness tests pass; harness code coverage ≥85% when coverage tooling configured.
- [ ] Source/data/repo hashes, issue status, and evidence paths saved; reports/ADRs updated.

### Mitigations
- R8/R12 → S4-T1; R9/R11 → S4-T2 and S4-T3.

## Capacity estimate and reconciliation (Step 4)
**ASSUMPTION:** one agent, 13 productive hours/week × 10 weeks = **130 hours**. Scope gets cut rather than shrinking task estimates if capacity falls.

| Bucket | Hours | Reconciliation |
|---|---:|---|
| Sprint 0 | 18 | sum of S0 tasks |
| Sprint 1 | 22 | sum of S1 tasks |
| Sprint 2 | 22 | sum of S2 tasks |
| Sprint 3 | 22 | sum of S3 tasks |
| Sprint 4 | 18 | sum of S4 tasks |
| **Tasks subtotal** | **102** | 18+22+22+22+18 |
| Slack ~15% (rounded) | 16 | ~15.7% of 102, unallocated issue buffer |
| Extra documentation reserve | 4 | final polish beyond task-defined docs |
| Additional owner validation/review | 6 | approvals, evidence verification, no guaranteed advisor |
| **Forecast total** | **128** | ≤130 h capacity |
| **Remaining capacity** | **2** | no discretionary major feature |

**High-uncertainty ranges (optimistic / likely / pessimistic):** S0-T1 graph interface 2/4/6 h (capped 4h spike; spill blocked); S1-T2 graph bridge 3/6/10h (cut graph-only extras beyond 6); S2-T3 vulnerable-symbol mapping 3/5/9h (no DB mutation without contract); S3-T3 heavy projects 4/6/10h (use timeout caps). High-end exceeds capacity; apply cuts below and re-estimate after spike.

## Critical path and task dependencies
```text
S0-T1 ──> S0-T2 ──> S0-T3 ─────────────┐
   └────> S0-T4 ──> S1-T1 ──> S1-T2 ──> S1-T3 ──> S4-T2 ──> S4-T3 ──> S4-T4
                                      ├──> S1-T4 ────┘
                                      └──> S2-T1 ──> S2-T2 ──────────┘
              S0-T4 ──> S2-T3 ──> S2-T4 ──> S3-T1 ──> S3-T2 ──> S3-T3 ──> S4-T1
                                            └──────> S3-T4 ─────────────────┘
             S1-T1 ──> S1-T5                    S2-T3 ──> S2-T5
```
The schematic shows major gates; task file `depends_on` is authoritative. True longest chain is computed from task DAG after estimation, not asserted by picture alone.

## Ordered cut policy and triggers (Step 8)
- **Trigger:** any sprint more than **3 calendar days** late or capacity forecast >130h → record cut decision with owner, update requirement priority and affected tests. Must never change expected result to pass.
1. Cut C1 (lowest impact): optional extra SWARM-CG adapter variants after full corpus eligibility documentation; no double count.
2. Cut C2: additional Vul4Py runnable cases (retain availability/transferability decision).
3. Cut C3: runtime-heavy baseline deployments, e.g., VulnReach services (retain comparator feasibility and valid-scope comparison note).
4. Cut C4: second-pass Wagtail/Saleor graph depth; retain attempted bounded scans and pinned evidence.
5. Cut C5 (needs owner approval): reduce 6 target repos to **4**, prioritizing controlled VulnReach lab, PyGoat, Django RealWorld, FastAPI; must amend REQ-09/acceptance and report scope reduction.

## Stub/fake plan
S0-T3 creates fake process outputs for exit 0/1/2 and fixture contract records. S1 adapters initially consume a fake graph projection. Switch to real graph only after ADR-001; failures must retain status `unsupported`. This unblocks independent adapter work while respecting strict interface contracts.

## Release and debt (Steps 9–10)
- Progress log in `tracking/progress-log.md`; debt `tracking/debt-backlog.md` with `DT-xx` owner/verification.
- After S4-T4: freeze benchmark changes, run all relevant QGs on clean environment, compile Keep a Changelog style release notes, SemVer release candidate, rollback plan, owner-approved publication and postmortem (estimated vs actual, cuts, debt migration).
- No one may claim the artifact/report was published or release gates passed based only on this planning document.
