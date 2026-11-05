# 06 — Environments, one quality-gates table, and CI

## Environment separation
**Fetch phase (network permitted):** verify URLs/commit SHAs, retrieve source archives and schema, inspect licenses, seed a local OSV SQLite snapshot, cache required baseline binaries. Record all SHA256 hashes, Python/uv versions and access dates in `sources.lock.json`.

**Evaluation phase (no network):** `uv sync` must already be complete. Run `uv run --offline --no-sync ...` inside a sandbox with `--network none` (Linux Docker rootless or equivalent) or `unshare -n` when supported. Absence of traffic under a permissive network environment **does not** prove offline behavior; log enforcement mode and any unsupported isolation. No Docker socket in the sandbox. Repository source read-only; output writable only in designated scratch path; no application server/test scripts.

**CI phase:** run synthetic fixture/contract tests by default; large real-world corpora are opt-in offline jobs using pre-provisioned sources. Do not download arbitrary third-party repos in PR workflows.

## Single source of truth — uniform quality gates (all task DoDs reference QG IDs)
| ID | Gate | Command / measurement | Success |
|---|---|---|---|
| QG-00 | Planning integrity | `python3 scripts/validate_plan.py` (plan root) | 0 errors |
| QG-01 | Ruff lint | `uv run --offline --no-sync ruff check benchmarks/pyreach_eval` | exit 0 |
| QG-02 | Types | `uv run --offline --no-sync mypy benchmarks/pyreach_eval` | exit 0 (after S0 env provision; no untyped ignored areas) |
| QG-03 | Unit/contract tests | `uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests -q` | exit 0, ≥85% harness statement coverage measured with pytest-cov in CI |
| QG-04 | Case/source schema | `uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests/test_contracts.py -q` | 100% valid fixtures accepted, invalid rejected |
| QG-05 | SARIF/CLI | `uv run --offline --no-sync pytest benchmarks/pyreach_eval/tests/test_cli_sarif.py -q` | all eligible 0/1/2 and schema assertions pass |
| QG-06 | Offline isolation | invoke frozen fixture with network denied; archived execution log | 0 network access successes; if enforcement unavailable => blocked |
| QG-07 | Dataset provenance | review `benchmarks/sources.lock.json` and SHA checker | 100% evaluated files hash-verified |
| QG-08 | Security | scan benchmark source changes with available pinned local secret scan; no secrets, executed untrusted code or elevated Docker access | 0 high-impact security violations |
| QG-09 | Report integrity | scorer/report tests, cohort table | sums/denominators consistent; no pass claimed for unsupported |

**Important:** `mypy`, `ruff`, `pytest-cov`/SARIF validator may require adding dev dependencies after S0 repo audit. Do not claim a gate passed while executable missing. Once adopted pin versions in PyReach lockfile. Non-code task checks QG-00, QG-07, QG-09 plus relevant reviews.

## Branching/versioning
- One branch per task: `bench/SN-TM-short-slug`.
- One logical commit per task, suggested `test(benchmark): SN-TM <summary>`.
- Benchmark-harness interface contract SemVer tracked separately from product release, initial `1.0.0` once approved.
- Breaking contract → ADR + MAJOR; additive backward-compatible → MINOR; corrections → PATCH.

## Release strategy
Use dedicated local benchmark release `bench-v0.1.0-rc.1` (ASSUMPTION: tag is only created by owner approval). Clean checkout → cached offline install smoke → case+schema checks → reports → changelog → freeze → publish artifacts if permitted → rollback by reverting benchmark harness commit/tag and restoring previous source-lock/DB snapshot.

## Runner hazards
WSL2 `unshare` may lack required privileges; the agent must test one explicit network blocking approach and record environmental constraints. Docker Desktop Windows engine sharing is optional, not a condition for success; fallback isolated Linux container only with safe options. No unsafely mounting host Docker socket. PyReach exit `1` is **finding** not runner failure; preserve separately from process errors.
