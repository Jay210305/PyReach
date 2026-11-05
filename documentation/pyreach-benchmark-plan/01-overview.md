# 01 — Overview, users, and requirements

## Vision
A repeatable evaluation harness that provides defensible answers to: How accurate is the call graph? How accurately does vulnerability-symbol reachability classify known cases? Does PyReach run offline and produce CI-ready SARIF? How does it behave on real repositories?

## Consumers
1. PyReach maintainer: regressions and release decision; 2. security researcher: precision/recall, dataset provenance; 3. CI maintainer: exit-code + SARIF conformance; 4. developer: diagnostic unsupported cases and actionable reproduction commands.

## Requirements and MoSCoW (single source for IDs)
| Requirement | Priority | Objective; measurable acceptance | Task mapping |
|---|---|---|---|
| REQ-01 | Must | Frozen, provenance+license checked source catalog; 100% inputs identified by URL+commit+SHA | S0-T4 |
| REQ-02 | Must | CLI/SARIF walking skeleton produces 1 success + 1 error record with reproducible commands | S0-T1..S0-T3 |
| REQ-03 | Must | 233 unique micro-cases accounted for; graph scoring only on supported export | S1-T1..S1-T3 |
| REQ-04 | Must | All 5 curated macro graphs inventoried and eligible subset scored | S1-T4 |
| REQ-05 | Must | SWARM-CG Python fixtures inventoried; supported subset processed | S1-T5 |
| REQ-06 | Must | FASTEN five-package micro + Fabric macro attempted, evaluated at cross-package edge level | S2-T1..S2-T2 |
| REQ-07 | Must | Vulnerable symbol metadata has provenance; 36 approved positive/negative/unknown fixtures | S2-T3..S2-T4 |
| REQ-08 | Must | Vul4Py 100/60 paper compatibility + asset availability decision; no bogus reachability labels | S2-T5 |
| REQ-09 | Must | Six selected real repository paths pinned and scanned or explicitly blocked | S3-T1..S3-T3 |
| REQ-10 | Must | Comparable baselines in correct scope; no pip-audit 'reachability' confusion | S3-T4 |
| REQ-11 | Must | SARIF 2.1.0 / CLI 0-1-2 / offline scans pass all eligible contract tests | S4-T1 |
| REQ-12 | Must | Three repeated runs per eligible project; precision, recall, F1; benchmark coverage denominators | S4-T2 |
| REQ-13 | Must | Release candidate report, failure triage, owner-gated closeout | S4-T3..S4-T4 |
| REQ-14 | Must | One agent owner/sprint; offline plan lint for IDs, hours, links, dependencies | S0-T2, S4-T4 |
| REQ-15 | Should | Identify real-world symbolic vulnerable function cases from licensed public Safety samples | S2-T3 |
| REQ-16 | Could | Full paid Safety corpus / all Vul4Py instances with proper permissions | external subsequent cycle |
| REQ-17 | Won't | Execute arbitrary exploit scripts on host or infer exploitability from import-only evidence | never |

## Use-case flows
**UC1**: canonical graph dataset → fetch+pin → graph projection → canonical edge matching → metrics with denominator/error accounting.  
**UC2**: local OSV snapshot + fixture app → CLI offline scan → normalize SARIF → compare reachable/unreachable/unknown ground truth.  
**UC3**: pinned real repo → preflight lock/manifest + DB provenance → three scans → time/RSS/alerts/error rate.  
**UC4**: same saved inputs → baseline scan (only comparable outcomes) → discrepancy investigation.

## Decision boundaries
Only a case with verified vulnerable-symbol location *and* entry-to-symbol truth may contribute to reachability precision/recall. Package-only advisories contribute to SCA coverage, not symbol reachability. Unknowns remain separate; negative labels require complete fixture-level graph assumptions.

## Gates
All Must requirements fit the capacity envelope in `04`, subject to assumption approval and S0 spike. Any implementation mismatch → ADR, impact on roadmap, reapproval before work is marked Ready.
