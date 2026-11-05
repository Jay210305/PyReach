# 03 — Technical specification and interface boundaries

## Public PyReach interface (provided by owner; validate in S0-T1)
```bash
uv run --offline --no-sync pyreach /path/to/project --db-path ~/.pyreach/osv.db -o results.sarif
uv run --offline --no-sync pyreach /path/to/project --db-path ~/.pyreach/osv.db -f text
```
- Documented return codes: **0** clean / `--no-fail`; **1** reachable findings; **2** configuration/runtime error.
- Network must not be required **during analysis**. Dependency preparation and initial OSV DB provisioning may be online.
- Do not presume `-o`, `-f`, `--db-path` defaults beyond this documented syntax; verify help, stdout/stderr, default output, and true `--no-fail` semantics.
- Do not assume SARIF has raw call edges; only use output fields observed in S0 audit.

## Harness contracts (must be approved before Ready)
| Contract | Version | Producer → consumer | Gate |
|---|---|---|---|
| `docs/contracts/cli-adapter.md` | 1.0.0 | PyReach CLI → process adapter | exit 0/1/2, captured argv, SARIF |
| `docs/contracts/source-lock.md` | 1.0.0 | acquisition → runner | pinned commits and checksums |
| `docs/contracts/benchmark-case.md` | 1.0.0 | corpus adapter → runner/scorer | fixture labels, source references |
| `docs/contracts/graph-projection.md` | 1.0.0 | graph exporter → scorer | canonical edges or `unsupported` |
| `docs/contracts/vulnerable-symbol.md` | 1.0.0 | fixture curator → reachability scorer | provenance and schema versions |
| `docs/contracts/result-record.md` | 1.0.0 | runner/scorer → report | statuses, errors, denominators |
| `docs/contracts/report.md` | 1.0.0 | report renderer → user | no invented results |

Each contract contains valid/invalid examples and an error model. JSON schemas in code are required implementation deliverables (not assumed present); markdown is the source-of-truth until a schema file is generated and reviewed. Changes to schema require ADR; incompatible major bump.

## Canonical behavior
1. **Graph:** compare stable fully-qualified edges only after documented name normalization; excluded, external and unresolved edges separated and counted.
2. **Reachability:** classify `reachable`, `unreachable`, `unknown`. Unknown is not false or true; a missing output becomes `unreported` until resolution. Only closed-world negative fixtures establish `unreachable` ground truth.
3. **Deduplication:** PyCG's 206 are shared with PyAnalyzer 233; one set counted for micro metrics.
4. **OSV:** package/version advisory is not a vulnerable-symbol mapping. Audit SQLite schema; do not insert guessed schema. Use approved DB fixture generation (S2).
5. **Scoring:** collect macro/micro separately, micro- vs macro-averaged F1, project-specific outcomes, explicit denominators and unsupported counts.
6. **Performance:** setup-time excluded; 3 warm comparable offline runs; wall time monotonic, peak RSS; report env and cold/warm semantics.
7. **Reproducibility:** exact source hashes, OSV snapshot hash, lock file, exit code, SARIF hash, error category, tool versions.

## Common errors (structured in benchmark output, never overwrite PyReach CLI errors)
`SOURCE_UNAVAILABLE`, `LICENSE_RESTRICTED`, `SCHEMA_INVALID`, `SYMBOL_UNVERIFIED`, `GRAPH_EXPORT_UNSUPPORTED`, `BENCHMARK_NOT_APPLICABLE`, `TIMEOUT`, `RESOURCE_LIMIT`, `CLI_ERROR`, `OFFLINE_VIOLATION`, `UNKNOWN_TOOL_OUTPUT`, `BASELINE_INCOMPARABLE`. Each is recorded with stable code, message, phase and evidence path.

## Contract-first integration example
Valid input case: `case_id=reach-001`, pinned manifest, public vulnerability evidence, expected `reachable`; produces a run record with path evidence and classification. Invalid case: unsupported `expected_label=exploitable` → `SCHEMA_INVALID`; do not infer mapping. Details in the contracts.

## Blocking unknowns: timeboxed spikes before implementation Ready
- **SP-01 (S0-T1, ≤4h):** true CLI options, graph export feasibility, local DB schema. Output `docs/adr/adr-001-pyreach-adapter.md` (decision, consequences).
- **SP-02 (S0-T4, ≤4h):** available corpus trees, licenses, SCHEMA variants, workspace size. Output `docs/adr/adr-002-corpus-eligibility.md`.
- If either spike remains unresolved, **G2 stays pending**: no fictitious contract approvals, no graph-based numerical results.
