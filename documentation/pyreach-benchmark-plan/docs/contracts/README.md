# Interface contracts — v1.0.0 draft

**Contract status:** Proposed; see `tracking/approval-gates.md`. These describe the **benchmark harness** to implement, not undocumented current PyReach features. Before task Ready, run contract validation, review valid/invalid examples, and approve adapters; a breaking change requires ADR + MAJOR version.

| File | Interface |
|---|---|
| [cli-adapter.md](cli-adapter.md) | PyReach process boundary and documented exit codes |
| [source-lock.md](source-lock.md) | immutable acquisitions and eligibility |
| [benchmark-case.md](benchmark-case.md) | case/ground truth schema |
| [graph-projection.md](graph-projection.md) | canonical graph projection and scoring |
| [vulnerable-symbol.md](vulnerable-symbol.md) | OSV advisory-to-symbol evidence |
| [result-record.md](result-record.md) | per-run measurements and errors |
| [report.md](report.md) | audit-grade aggregated results |

**Shared error JSON** (benchmark harness, not PyReach CLI): `{"code":"SCHEMA_INVALID","phase":"normalize","message":"unsupported label","evidence_path":null}`. `code` is one of 03's enum; immutable `case_id` included in its parent run record. Invalid records are rejected early, never coerced to success.
