# Contract C-RESULT 1.0.0 — per-run result and error

## JSONL model
```json
{"schema_version":"1.0.0","run_id":"20261013-001","case_id":"reach-001","repeat_index":1,"source_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","osv_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","pyreach_commit":"cccccccccccccccccccccccccccccccccccccccc","scanner_exit_code":1,"run_status":"completed","prediction":"reachable","duration_s":1.25,"peak_rss_kib":42000,"sarif_path":"/tmp/results/reach-001.sarif","error":null,"argv":["uv","run","--offline","--no-sync","pyreach","/tmp/app","--db-path","/tmp/db","-o","/tmp/out.sarif"],"isolation":"network-denied"}
```
Types: `repeat_index:int>=1` identifies repeated measurements within a run; `scanner_exit_code:int|null`; `duration_s:float>=0`; `peak_rss_kib:int|null`; `prediction` ∈ `reachable/unreachable/unknown/unreported/not_applicable`; `run_status` ∈ `completed/unsupported/blocked/error`; `isolation` ∈ `network-denied/network-not-enforced/not-run`; `error` nullable `{code,phase,message,evidence_path}`. Source hash, db hash and PyReach SHA required for `completed`. Scanner exit 1 with findings is `completed`. Artifact paths are local, not public permanent URLs.

## Invalid example
`{"run_status":"completed","scanner_exit_code":2,"prediction":"unreachable"}` → `SCHEMA_INVALID` (runtime error is not a clean negative). Missing SHA on completed records → `SCHEMA_INVALID`.

## Classification rule
- `blocked`: cannot acquire license/source/env; `unsupported`: scanner lacks necessary analysis/output type; `error`: CLI fails/crashes or case validation fails; `completed`: code executed and fully recorded.
- A completed scanner run may make reachability `unknown`; completed does not mean correct.
- Case scores attach separately as `evaluation_status` and `ground_truth_label`; do not overwrite process observation.
- A run may be `completed` with `scanner_exit_code=0`, yet its truth comparison reveals a FN.

## Tests
Contract JSON-schema accepts valid sample, rejects invalid; duplicated `run_id+case_id+repeat` rejected; no report can erase errors or unknowns.
