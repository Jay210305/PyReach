# Technical debt backlog

| ID | Status | Location | Cause | Impact | Estimate | Verification / closure |
|---|---|---|---|---|---:|---|
| DT-01 | proposed | `benchmarks/pyreach_eval/graph/` | graph API unknown until S0 audit | benchmark might be unsupported | 3h | ADR-001 resolved, graph adapter contract tests |
| DT-02 | proposed | `benchmarks/pyreach_eval/cases/` | advisory-to-function metadata absent from standard OSV | unscorable reachability | 3h | source provenance + 36 fixture checks |
| DT-03 | proposed | project baselines | old package/framework runtime compatibility | inability to run some comparators | 2h | explicit blocked ledger, non-execution documentation |
| DT-04 | closed | `documentation/pyreach-benchmark-plan/tracking/progress-log.md` | S0 audit records controlled/blocked status without fabricated sources | accurate Windows platform record | 0.5h | S0-T1..T4 done |

Status names: proposed/open/in-progress/closed/deferred. At release, each row gets closed, explicitly dropped with reason, or migrated with owner/impact/context.
