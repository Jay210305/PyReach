# 05 — Evaluation and testing strategy

## Evaluation pyramid
1. **Contract tests:** JSON cases/results, source lock, canonical graph parsing, invalid/valid samples; red-first; no external network.
2. **Fixture tests:** 36 hand-reviewed vulnerability fixtures (12 reachable, 12 unreachable, 12 unknown). Use explicit entry points and symbol provenance; fixtures should be small and deterministic.
3. **Reference graph benchmarks:** 233 unique PyAnalyzer micro, 5 manual curated macro, SWARM-CG Python subset, FASTEN micro + Fabric macro. Verify test universe and exclusion reasons before summarizing.
4. **Project integration:** VulnReach lab and PyGoat, Django RealWorld and FastAPI, Saleor and Wagtail. Pin SHA, manifest root, Python constraints. Use static offline scanning; no execution of apps.
5. **Nonfunctional:** SARIF JSON-schema, CLI exit codes 0/1/2, network namespace, repeated perf, memory, error classes and robustness.

## Ground-truth constraints
- PyAnalyzer micro: expected `callgraph.json` next to source; discover paths using file tree, do not hardcode unverified locations. PyAnalyzer holds 206 borrowed PyCG cases plus 27 added.
- PyAnalyzer macro C: 5 manually curated project call graphs; only count edges whose identity is resolvable under both tools. If a call resolves in benchmark but not in PyReach, record either FN or unsupported based on predeclared eligibility rules—**not post-hoc to improve score**.
- FASTEN `benchmark/micro`: root + dep1/dep2 + trans-dep1/trans-dep2. Fabric macro has stitched reference; distinguish PyReach graph format from FASTEN precomputed graphs.
- SWARM-CG: verify Python ground-truth format, overlap with PyCG, and applicable runnable cases; never double-count.
- Safety: source-level publicly accessible Python samples only, subject to license check; no access assumption for full 13k+ commercial records.
- Vul4Py: paired exploit/functional oracles evaluate *repair*, not necessarily dependency symbol reachability. Classify case-by-case relevance.

## Case scoring protocol
For a separately pre-labeled and eligible binary set: TP is an actual `reachable` predicted reachable; FP is a labeled unreachable predicted reachable; FN is a labeled reachable predicted unreachable; TN is labeled unreachable predicted unreachable. Predictions `unknown`/`unreported` are **abstentions**, reported separately with coverage and conservative sensitivity bounds; do **not** quietly drop them. Report confusion matrix on decided predictions plus all-case coverage and abstention fractions. Ground-truth unknown cases measure correct uncertainty handling and are not binary-classification TNs.

Report:
- `precision=TP/(TP+FP)`; `recall=TP/(TP+FN)` on decided subset, only if denominators >0;
- `F1=2PR/(P+R)`; `coverage=decided/eligible`; unsupported and blocked separate from eligible;
- graph `edge_precision=matched_pred/pred`, `edge_recall=matched_gold/gold`, and strict path success where reference path is given;
- `unknown_label_accuracy` on 12 unknown ground-truth cases; no false certainty (`reachable` or `unreachable`) for unknown unless manually adjudicated;
- confidence intervals/variance only if appropriate to measured sample.

## Acceptance gates (target, not preclaimed outcomes)
- 100% suite case IDs unique; 100% selected source commits pinned; 100% case records schema-valid.
- Attempt 233 micro tests, 5 curated macros, FASTEN micro/macro; publication includes coverage/exclusion table.
- 36 labeled fixtures reviewed; 100% are represented in run ledger even when skipped/blocked.
- 100% eligible SARIF files schema-validate; 100% CLI contract fixture cases have correct exit codes; 0 outbound network attempted under offline isolation.
- 3 repeats × each eligible real repo; store median/p95/RSS or `blocked` reason, not made-up metrics.
- Quality threshold is **measurement completeness**, not an unverified minimum F1. Any threshold for release pass must be approved post-baseline with ADR.

## TDD and replay
Write failing test before adapter/scorer change. Frozen offline fixtures only. Do not run third-party project tests or execute exploit proofs. Use generated `benchmarks/reports/<run-id>/` artifacts; compare SHA-stable inputs across baseline tools.
