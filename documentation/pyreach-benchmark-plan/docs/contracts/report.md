# Contract C-REPORT 1.0.0 — final evaluation bundle

## Files and schema
Each frozen run directory contains `summary.json`, `summary.csv`, `case-results.jsonl`, `REPORT.md`, `sources.lock.json`, `run-config.json`, `discrepancies.md`, and retained eligible SARIF files (or paths/hashes where copying prohibited).

JSON summary requires:
```json
{"schema_version":"1.0.0","run_id":"20261013-001","dataset":{"eligible":36,"scored_binary":24,"unknown_ground_truth":12,"abstentions":0,"unsupported":0,"blocked":0,"errors":0},"confusion":{"tp":12,"fp":0,"fn":0,"tn":12},"precision":1.0,"recall":1.0,"f1":1.0,"measurements_are_real":false}
```
**This is an illustrative mock** for contract tests, NEVER a claim that PyReach achieved 100%. `measurements_are_real=false` forbids publishing it as measured data. Real measured reports must set true only when evidence files exist and hashes validate. `undefined` metrics use JSON null and explanation, never NaN or automatic 0.

## Invalid example
`{"dataset":{"scored_binary":24},"confusion":{"tp":10,"fp":5,"fn":5,"tn":5}}` → `SCHEMA_INVALID` (confusion counts sum 25 ≠ 24). `measurements_are_real=true` with no case evidence → report generation fails `SOURCE_UNAVAILABLE`.

## Outputs and acceptability
- Per-suite graph metrics / reachability metrics isolated in separate tables.
- The status table includes **eligible**, **scored**, **unknown**, **unsupported**, **blocked**, **error**, with reconcile checks (no double counting).
- Real repo report states size, commit, manifest path, scanned entry-point assumptions, OSV SHA, runtime, RSS, SARIF validity and false-claim restrictions.
- Baseline table restricts package-detection comparators vs call-graph comparators vs reachability comparators; never compare unrelated F1 values.
- Security notes explicitly forbid claiming static reachability guarantees exploitability.
