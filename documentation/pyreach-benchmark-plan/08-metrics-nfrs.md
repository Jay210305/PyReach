# 08 — Metrics, NFRs and evidence

## Outcome metrics (definitions; not claimed results)
| ID | Definition | Minimum report content |
|---|---|---|
| K-01 | Edge micro/macro precision, recall, F1 | TP/FP/FN edges, separately per suite, exclusions |
| K-02 | Reachability binary precision, recall, F1 | TP/FP/FN/TN on decided eligible labels |
| K-03 | Coverage and abstention | eligible / scored / unknown / unreported / unsupported / blocked / error counts |
| K-04 | Unknown conservatism | correctly reported unknown / 12 unknown-label cases | 
| K-05 | Dependency/advisory recall vs package baseline | same package/version snapshot; only when inputs comparable |
| K-06 | Execution and size | 3-repeat median, p95 (descriptive from 3 repeats), peak RSS, LOC/files and HW/env |
| K-07 | Contract compliance | percentage eligible SARIF valid, CLI behavior cases passed, CI gate parity |
| K-08 | Offline proof | isolation method, successful network calls (must be zero), enforcement availability |
| K-09 | Reproducibility | % evaluated runs with Git+DB+schema+binary hashes (target 100%) |
| K-10 | Security process | 0 executed third-party setup/exploit programs on host; 0 token exposures |

## NFRs and targets (provisional assumptions)
- NFR-01: all benchmark harness operations deterministic for frozen case inputs unless timing; sorted canonical edges and stable serializations.
- NFR-02: no network during scan, artifact dependencies predownloaded and hashed.
- NFR-03: max **120 s** small case and **900 s** large project scan *time-out*, **not PyReach performance requirement*; mark TIMEOUT separately; adjust only by ADR.
- NFR-04: default cap **8 GiB RSS** per evaluation worker (ASSUMPTION based on unknown host; adjust after environment audit). Exceeding resource cap is not a false positive/negative.
- NFR-05: harness tests ≥85% statement coverage; explicit schema tests for all boundaries.
- NFR-06: every result includes `case_id`, source SHA, PyReach SHA, OSV SHA, argv, timestamps, exit, run status, evidence path, error code.
- NFR-07: no production CLI interface changes for benchmarking without explicit approval.

## Statistical handling
Report raw counts and conditional rates with denominator. On n=3 performance repeats, label p95 as empirical rather than population estimate. If one scan times out, do not compute median only across successful samples without stating censored runs. Stratify by PyAnalyzer borrowed/new, test complexity, dependency depth, framework, and source parser support.

## Evidence naming
`benchmarks/reports/YYYYMMDD-runid/{run-config.json,source-manifest.json,case-results.jsonl,summary.json,summary.csv,findings/*.sarif,process/*.json,discrepancies.md,REPORT.md}`.
Each path is a **future implementation artifact**, not included as measured evidence in the planning ZIP.
