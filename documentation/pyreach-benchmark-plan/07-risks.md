# 07 — Risk register

| ID | Risk | Probability / impact | Owner | Mitigation / linked task | Trigger / response |
|---|---|---|---|---|---|
| R1 | PyReach has no graph-export API | H/H | benchmark-agent | S0-T1 ADR; S1-T2 conditional internal read-only bridge | no export after spike → graph status `unsupported`, never synthetic precision |
| R2 | SQLite OSV lacks vulnerable-symbol data | H/H | benchmark-agent | S2-T3 source provenance and controlled data integration | symbol cannot be verified → unknown, no fake mapping |
| R3 | Benchmarks format or repo changed | M/M | benchmark-agent | S0-T4 pin commit; S1-T1 eligibility adapter | incompatible schema → record blocked + ADR |
| R4 | Dataset benchmark overlap causes inflated N | H/M | benchmark-agent | S1-T1 dedup PyCG within PyAnalyzer; S1-T5 SWARM overlap | duplicate canonical case → fail contract test |
| R5 | Safety data licensing or Vul4Py availability | H/M | benchmark-agent | S2-T3 / S2-T5; public-only licensed samples | no grant/assets → `LICENSE_RESTRICTED` / `SOURCE_UNAVAILABLE` |
| R6 | Legacy Django RealWorld unsafe on new Python | H/M | benchmark-agent | S3-T2 static only; no execution/import | dependency install needed → blocked static fallback |
| R7 | Untrusted repo setup/exploit executes | M/H | benchmark-agent | S0-T3 isolation, S3 tasks static-only | untrusted code execution request → stop and escalate |
| R8 | Offline verification silently contacts host network | M/H | benchmark-agent | S4-T1 isolated network enforcement | cannot isolate → offline gate blocked, no offline claim |
| R9 | Performance budget exceeds 13h/week plan | M/M | benchmark-agent | S3-T3 timeout/resource cap, ordered scope cuts | sprint >3 calendar days late → apply cut order |
| R10 | Comparator tools measure different scope | H/M | benchmark-agent | S3-T4 baseline protocol | missing same ground truth → separate table, no false apples-to-apples |
| R11 | Missing partial call-graph edges treated as negative truth | H/H | benchmark-agent | S2-T4 12 unknown controls; S4-T2 abstention accounting | uncertainty erased → report gate fails |
| R12 | SARIF schema / CLI flags differ from assumed | M/M | benchmark-agent | S0-T1 CLI contract, S4-T1 schema test | mismatch → update documented contract via ADR first |

## Timebox response
A spike ≤4 h that cannot resolve an unknown must yield a written decision: defer graph-only scoring, substitute eligible fixture evidence, or request maintainer API access; it **must not** silently consume the next sprint.

## Escalation
On critical misclassification, exploit execution, leakage, or unauthorized source use: stop related task, preserve evidence, log blocker, seek owner approval. Unknown must remain unknown.
