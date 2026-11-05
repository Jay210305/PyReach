# Implementation task index and agent execution protocol

**Version:** 0.1.0-draft | **Document date:** 2026-10-13 | **Maintainer:** PyReach owner (approval pending) | **Executor:** benchmark-agent.

## Task index
| ID | File | Owner | Effort (h) | Status |
|---|---|---|---:|---|
| S0-T1 | [audit-existing-pyreach](sprint-0-walking-skeleton-and-hard-feasibility/S0-T1-audit-existing-pyreach.md) | benchmark-agent | 4 | todo |
| S0-T2 | [freeze-harness-contracts](sprint-0-walking-skeleton-and-hard-feasibility/S0-T2-freeze-harness-contracts.md) | benchmark-agent | 4 | todo |
| S0-T3 | [walking-skeleton-cli](sprint-0-walking-skeleton-and-hard-feasibility/S0-T3-walking-skeleton-cli.md) | benchmark-agent | 6 | todo |
| S0-T4 | [pin-datasets-and-licenses](sprint-0-walking-skeleton-and-hard-feasibility/S0-T4-pin-datasets-and-licenses.md) | benchmark-agent | 4 | todo |
| S1-T1 | [normalize-pyanalyzer-pycg](sprint-1-reference-python-graph-evaluation/S1-T1-normalize-pyanalyzer-pycg.md) | benchmark-agent | 6 | todo |
| S1-T2 | [project-pyreach-graph](sprint-1-reference-python-graph-evaluation/S1-T2-project-pyreach-graph.md) | benchmark-agent | 6 | todo |
| S1-T3 | [score-pyanalyzer-micro](sprint-1-reference-python-graph-evaluation/S1-T3-score-pyanalyzer-micro.md) | benchmark-agent | 4 | todo |
| S1-T4 | [score-five-macro-graphs](sprint-1-reference-python-graph-evaluation/S1-T4-score-five-macro-graphs.md) | benchmark-agent | 4 | todo |
| S1-T5 | [triage-swarm-cg](sprint-1-reference-python-graph-evaluation/S1-T5-triage-swarm-cg.md) | benchmark-agent | 2 | todo |
| S2-T1 | [evaluate-fasten-micro](sprint-2-cross-package-and-vulnerability-truth/S2-T1-evaluate-fasten-micro.md) | benchmark-agent | 5 | todo |
| S2-T2 | [evaluate-fasten-fabric](sprint-2-cross-package-and-vulnerability-truth/S2-T2-evaluate-fasten-fabric.md) | benchmark-agent | 5 | todo |
| S2-T3 | [curate-osv-symbol-labels](sprint-2-cross-package-and-vulnerability-truth/S2-T3-curate-osv-symbol-labels.md) | benchmark-agent | 5 | todo |
| S2-T4 | [build-thirty-six-reachability-cases](sprint-2-cross-package-and-vulnerability-truth/S2-T4-build-thirty-six-reachability-cases.md) | benchmark-agent | 5 | todo |
| S2-T5 | [assess-vul4py](sprint-2-cross-package-and-vulnerability-truth/S2-T5-assess-vul4py.md) | benchmark-agent | 2 | todo |
| S3-T1 | [scan-vulnreach-and-pygoat](sprint-3-six-real-world-project-scans-and-baselines/S3-T1-scan-vulnreach-and-pygoat.md) | benchmark-agent | 6 | todo |
| S3-T2 | [scan-django-and-fastapi](sprint-3-six-real-world-project-scans-and-baselines/S3-T2-scan-django-and-fastapi.md) | benchmark-agent | 6 | todo |
| S3-T3 | [scan-saleor-and-wagtail](sprint-3-six-real-world-project-scans-and-baselines/S3-T3-scan-saleor-and-wagtail.md) | benchmark-agent | 6 | todo |
| S3-T4 | [run-comparable-baselines](sprint-3-six-real-world-project-scans-and-baselines/S3-T4-run-comparable-baselines.md) | benchmark-agent | 4 | todo |
| S4-T1 | [verify-sarif-ci-offline](sprint-4-offline-ci-proof,-statistics-and-stabilization/S4-T1-verify-sarif-ci-offline.md) | benchmark-agent | 5 | todo |
| S4-T2 | [compute-performance-and-rates](sprint-4-offline-ci-proof,-statistics-and-stabilization/S4-T2-compute-performance-and-rates.md) | benchmark-agent | 5 | todo |
| S4-T3 | [stabilize-and-triage](sprint-4-offline-ci-proof,-statistics-and-stabilization/S4-T3-stabilize-and-triage.md) | benchmark-agent | 4 | todo |
| S4-T4 | [close-release-and-postmortem](sprint-4-offline-ci-proof,-statistics-and-stabilization/S4-T4-close-release-and-postmortem.md) | benchmark-agent | 4 | todo |

## Critical-path map
```text
S0-T1 -> S0-T2 -> S0-T3 -> S2-T4 -> S3-T1 -> S3-T2 -> S3-T3 -> S4-T1 -> S4-T3 -> S4-T4
  \-> S0-T4 -> S1-T1 -> S1-T2 -> S1-T3 -> S4-T2 ---^
                  \-> S2-T1 -> S2-T2 -> S4-T2
```
All edges are verified in YAML `depends_on`; graph includes additional noncritical tasks (S1-T4/T5, S2-T3/T5, S3-T4). Critical path ordering is conceptual; actual duration depends on calendar allocation.

## Cross-cutting execution rules
- **Strict gate order:** discovery → constraints → spec/spikes → roadmap/capacity → contracts → task execution → closeout. Whole plan generated as draft by user request; acceptance still pending.
- **TDD:** write a failing test/explicit verifiable checklist before implementation. Subtasks ≤2h, tasks ≤8h; merge independently, one commit/task, branch `bench/SN-TM-slug`.
- **Determinism:** frozen input hashes, fixed source/DB versions, canonical sorting; network-only acquisition before offline runs.
- **Safety:** source repos treated as data; no third-party setup scripts/exploit execution, no Docker socket mount, bounded memory and time; redact secrets.
- **Semantics:** no PyReach graph export assumed; unsupported is not negative truth, scanner exit 1 means findings not crash. No package-only CVE counted as vulnerable function.
- **Code style:** typing, ruff/mypy, pytest red→green, 85% harness coverage where environment configured, QG table in `06-ci-cd-environments.md` is sole authority.
- **Reporting:** generate confusion metrics only from ground-truth eligible cases; record unknown/blocked/error separately.

## Document control
| Version | Date | Changes | Approved by |
|---|---|---|---|
| 0.1.0-draft | 2026-10-13 | Initial complete 5 sprint / task-card plan; no benchmarks executed | PENDING |

## Plan lint
Run from the plan root `python3 scripts/validate_plan.py`: check unique IDs, DAG, task-level caps, subtask ≤2h, sum subtasks=task, sum task=sprint, links in plan, roadmap hours, requirement→task coverage. Corrections require updating index/roadmap consistently.
