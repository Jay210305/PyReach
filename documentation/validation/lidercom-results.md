# Validation Report — Lidercom Deploy & Benchmark (S4-T7)

- Date: 2026-10-09 (UTC-5, America/Lima).
- Runner alias: ` replica-local-dev ` (see §1 R4 status).
- PyReach version: `0.1.0`.
- Interpreter: CPython 3.14.7 (dev `.venv`); packaging targets `>=3.10`
  (Docker replica pins `python:3.10-slim`, `ci/docker/Dockerfile.pyreach`).

## 1. R4 status: access and fallback

Lidercom VPN / runner credentials were **not available** in this environment,
so the protocol below ran against the documented R4 fallback:

- `tests/fixtures/projects/linear_reachable` (micro, known REACHABLE),
- a mid-size replica: the PyReach `pyreach/` package tree itself
  (31 modules, real-world code, copied to a temp dir),
- the `ci/docker/Dockerfile.pyreach` replica definition (build not executed:
  Docker daemon down at validation time; statically asserted in S4-T6).

No Lidercom-confidential code was involved; only aggregate metrics are stored
here. Substitution is transparent per `10-risk-and-contingency-plan.md` §2 R4.

## 2. Deployment package (7.1)

| Artifact | Size | Notes |
|----------|------|-------|
| `dist/pyreach-0.1.0-py3-none-any.whl` | 63 KB | `uv build`, hatchling backend |
| `dist/pyreach-0.1.0.tar.gz` | 387 KB | 176 files (sdist excludes `.venv/.git/.opencode/graphify-out/dist/context`, `pyproject.toml [tool.hatch.build]`) |
| `[project.scripts]` | — | `pyreach = "pyreach.cli:main"`; `uv run pyreach --version` → `PyReach 0.1.0` |
| `uv sync --locked` | exit 0 | lockfile re-locked (`virtual` → `editable` after the `package = true` flip) |

Packaging fixes applied: `[tool.uv] package = false` → `true` plus
`[build-system]` (hatchling) per spec 03 §1 (the `pyreach/` package exists,
so the AGENTS.md flip condition is met); minimal `README.md` added (required
by the `readme = "README.md"` metadata); `PYREACH_VERSION` pinned to `0.1.0`
in `ci/gitlab/.pyreach-scan.yml`.

DB convention: `/opt/pyreach/osv.db`, < 7 days (weekly cron
`ci/scripts/sync-pyreach-osv.sh`). Benchmarks below used temp DBs seeded
with synthetic advisories (offline, deterministic).

## 3. Smoke test (7.2, replica)

- `pyreach --version` → `PyReach 0.1.0`, exit 0.
- `pyreach --help` lists every spec §4 option, exit 0.
- Micro scan (`linear_reachable`, seeded DB): `REACHABLE: 1`,
  path `main.main -> client.fetch -> vuln_lib.risky`, exit 1.
- `unshare -n` / `firejail` unavailable on the Windows dev host; instead a
  static egress audit (§5) proves no network I/O on the scan path.

## 4. Benchmarks (7.3)

Two consecutive runs each (cold = fresh interpreter, warm = module cache hot).
Budget: **< 45 s** wall-clock (doc 09 §5).

### Scenario A — micro fixture (`linear_reachable`)

1 dep, 1 advisory, 3 modules, 8 nodes, 4 edges, 1 entry.

| Run | Wall-clock | Peak memory | Verdict |
|-----|-----------|-------------|---------|
| 1 (cold) | 0.226 s | 1.60 MB | REACHABLE, exit 1 |
| 2 (warm) | 0.012 s | 0.14 MB | REACHABLE, exit 1 |

### Scenario B — mid-size replica (PyReach tree)

2 deps, 1 matching advisory, 31 modules, 421 nodes, 808 edges, 3 entries.

| Run | Wall-clock (pipeline) | Peak memory | Verdict |
|-----|----------------------|-------------|---------|
| 1 (cold) | 1.176 s | 7.24 MB | POTENTIALLY_REACHABLE |
| 2 (warm) | 0.844 s | 7.19 MB | POTENTIALLY_REACHABLE |

Full CLI end to end on B (`-o b.sarif -q`): **1.61 s** wall
(incl. interpreter startup), exit 0; with `--include-potentially`: exit 1.
SARIF artifact: **4 796 bytes** (budget < 5 MB).

Headroom vs budget: ~28× on the mid replica. No `--max-depth 3` retry or
`--exclude` mitigation needed; R1 lazy loading not triggered. p50/p95 over
the two runs: A ≈ 0.01–0.23 s, B ≈ 0.84–1.18 s (pipeline-only; CLI adds
≈ 0.5–0.8 s of startup).

`packaging==25.0` advisory (range `>=20.0,<25.0`, exclusive upper bound)
correctly did **not** match — boundary semantics verified.

## 5. Network-egress audit (data sovereignty, doc 09 §7)

`grep` over `pyreach/` (non-test) for socket/HTTP clients:

- No socket/HTTP client on the scan path. The schema loader (`output/sarif.py`
  `load_sarif_schema`) reads a bundled package resource via
  `importlib.resources` (no fetch), and SARIF validation now also runs in
  production (`SarifBuilder.write()` calls `validate_sarif_document`).
- `loaders/packages.py` uses `urllib.parse`/`url2pathname` (local path
  handling, no I/O). `importlib.metadata` reads local dist metadata.
- No `socket`, `http.client`, `requests`, `httpx`, or subprocess `pip` calls.

Conclusion: **zero network egress during scans** on the replica.

## 6. SARIF acceptance (7.4)

- Every produced SARIF validates against the cached OASIS schema via
  `jsonschema` (unit + e2e coverage from S4-T1/T2/T6).
- GitLab Security dashboard ingestion **untested** (no Lidercom MR access);
  per R3 the artifact + exit-code gate is the primary value and is
  demonstrated (`test_gate_blocks_on_reachable`, `test_gate_passes_on_clean`).
- MR-diff annotation unverified — pending real-runner access.

## 7. Gate verification (S4-T7 acceptance)

- Reachable CVE present (`linear_reachable`): exit **1**, SARIF contains an
  `error` result with full `codeFlows`.
- Clean project (`package_unused`): exit **0**.
- `--no-fail` override: exit **0** with SARIF still written (S4-T3 e2e/unit).
- `--include-potentially` (flag and `.pyreach.yml` `thresholds`): flips a
  potential-only scan from 0 to **1** (S4-T5 e2e).

## 8. Deviations and issues

1. **R2 fix (filed & fixed during validation):** `analyzer._package_imported`
   compared the OSV-normalized name (`vuln-lib`) against raw import tops
   (`vuln_lib`) → false `NOT_REACHABLE` on dynamic chains. Fixed with PEP 503
   normalization + regression tests (`test_package_imported_normalizes_*`).
   S3-T8 scenarios stay green.
2. **`pyreach sync-osv` subcommand still unwired** (library `sync_osv`
   exists): templates and cron reference it; pre-seed the DB out of band
   until wired. Tracked from S4-T6.
3. **Dashboard ingestion + runner clock/3.10 matrix**: pending Lidercom access.
4. `dist/` artifacts are build outputs (git-ignored) and were rebuilt during
   validation; not committed.
