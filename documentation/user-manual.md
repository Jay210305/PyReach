# PyReach User Manual

*Last updated for v0.1.0. Every command below was verified against the
shipped CLI; sample outputs are abridged real runs.*

## 1. Installation

Requirements: Python 3.10+, [uv](https://docs.astral.sh/uv/) (recommended).

```powershell
git clone <repo-url> pyreach
cd pyreach
uv sync              # create .venv and install runtime + dev dependencies
uv run pyreach --version   # -> PyReach 0.1.0
```

Alternative (from a built wheel, no build step):

```powershell
uv build               # produces dist/pyreach-0.1.0-py3-none-any.whl
pip install dist/pyreach-0.1.0-py3-none-any.whl
pyreach --version
```

## 2. First scan

PyReach reads a local OSV database (no network during scans). Create it from a
local PyPI OSV archive, or omit `--source` to download the current PyPI archive
during this explicit sync command:

```powershell
uv run pyreach sync-osv --source C:\path\to\PyPI\all.zip --db-path demo-osv.db
```

Scan a project (here the bundled `linear_reachable` demo):

```powershell
uv run pyreach tests/fixtures/projects/linear_reachable -f text --db-path demo-osv.db
```

The summary lists the advisories that match installed dependencies. An empty
database would produce this summary, but it cannot provide a real scan:

```text
PyReach 0.1.0 - Static Reachability Analysis
=============================================
Project: .../linear_reachable
Entry points: (none)
Max depth: 5

Results Summary:
----------------
REACHABLE:              0
POTENTIALLY REACHABLE:  0
NOT REACHABLE:          0
TOTAL:                  0
```

`sync-osv` accepts a local JSON/JSONL/ZIP source or the default HTTPS PyPI
archive. Keep the sync step outside an offline CI scan runner.

## 3. Command reference

```text
usage: pyreach [-h] [-m MANIFEST] [-d DB_PATH] [-o OUTPUT] [-e ENTRY_POINT]
               [-k MAX_DEPTH] [--include-potentially] [--include-all]
               [--no-fail] [-f {sarif,json,text}] [--exclude EXCLUDE]
               [--cache | --no-cache] [-v] [-q] [--version]
               [PROJECT_PATH]

usage: pyreach sync-osv [-h] [--db-path DB_PATH] [--source SOURCE]
                        [--incremental] [-v] [-q]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `PROJECT_PATH` | | (required) | Root directory of the project to analyze |
| `--manifest` | `-m` | `requirements.txt` | Manifest file (falls back to `Pipfile.lock` when present) |
| `--db-path` | `-d` | `~/.pyreach/osv.db` | Local OSV SQLite database |
| `--output` | `-o` | `pyreach-results.sarif` / `.json` | Output file (`text` prints to stdout unless `-o` is given) |
| `--entry-point` | `-e` | auto-detect | Entry point FQN, repeatable (merged with detected) |
| `--max-depth` | `-k` | `5` | Traversal depth, 0–7 |
| `--include-potentially` | | off | Fail (exit 1) on `POTENTIALLY_REACHABLE` too |
| `--include-all` | | off | Include `NOT_REACHABLE` results in output |
| `--no-fail` | | off | Always exit 0 on findings (errors still exit 2) |
| `--format` | `-f` | `sarif` | `sarif` \| `json` \| `text` |
| `--exclude` | | none | Path pattern to exclude, repeatable (e.g. `tests/`) |
| `--cache` / `--no-cache` | | on | Call-graph cache hint (currently in-memory build) |
| `--verbose` | `-v` | off | DEBUG logging (includes tracebacks) |
| `--quiet` | `-q` | off | Suppress progress/summary (CI mode) |
| `--version` | | | Print version and exit |

Notes:

- `--entry-point` accepts `pkg.mod:func` or `pkg.mod.func` (equivalent).
- `--exclude` affects which files are parsed; findings stay conservative —
  an excluded library still resolves through placeholder nodes, so exclusions
  never hide reachability, they only drop file/line details.
- `--cache` is accepted for forward compatibility; the build is in-memory.

## 4. Exit codes

| Code | Meaning | CI behavior |
|------|---------|-------------|
| 0 | No reachable findings (or `--no-fail`) | Pipeline continues |
| 1 | Reachable findings (plus potentially-reachable with `--include-potentially`) | Pipeline blocked |
| 2 | Configuration/runtime error | Pipeline blocked (infra issue) |

PowerShell:

```powershell
uv run pyreach ./myapp --db-path ~/.pyreach/osv.db
$LASTEXITCODE   # 0, 1 or 2
```

POSIX shells: same command, then `echo $?`.

## 5. Configuration (`.pyreach.yml`)

Optional project file (strict: unknown keys are an error, exit 2):

```yaml
pyreach:
  version: "1"
  entry_points:
    - "myapp.cli:main"
    - "myapp.api.init_routes"
  ignore_paths:
    - "tests/"
    - "docs/"
  max_depth: 5
  manifest: "requirements.txt"
  osv_db: "~/.pyreach/osv.db"
  thresholds:
    fail_on_reachable: true
    fail_on_potentially: false
```

Precedence (highest first):

1. CLI flags explicitly passed
2. Project `.pyreach.yml` (or `.pyreach.yaml`)
3. User-global `~/.pyreach/config.yml` (same schema)
4. Built-in defaults

`entry_points` and `ignore_paths`/`--exclude` merge (config + CLI);
`--include-potentially` ORs with `thresholds.fail_on_potentially`.

`thresholds.fail_on_reachable: false` keeps `REACHABLE` findings from failing
the scan (exit 0) — the SARIF/JSON still lists them. Use sparingly (e.g.
monitoring mode); CI gating relies on the default `true`. There is no CLI flag
that re-enables it; change the config value to restore gating.

## 6. Output formats

With advisories matching, a text scan looks like this (abridged real run,
exit code `1`):

```text
Results Summary:
----------------
REACHABLE:              1
POTENTIALLY REACHABLE:  0
NOT REACHABLE:          0
TOTAL:                  1

Reachable CVEs:
  - CVE-2026-00001 (CRITICAL) in vuln-lib==1.0.0
    Path: main.main -> client.fetch -> vuln_lib.risky
    File: vuln_lib/__init__.py:1
```

Statuses: `REACHABLE` (static path entry → vulnerable symbol),
`POTENTIALLY_REACHABLE` (dynamic/unresolved constructs prevent ruling it
out — uncertainty always escalates, never downgrades), `NOT_REACHABLE`
(no path, package not imported, imports fully resolved).

SARIF (`-f sarif`, default) — one `run`, portable `PROJECT_ROOT` base:

```json
{
  "ruleId": "PYREACH-REACHABLE-CVE",
  "level": "error",
  "message": {"text": "CVE-2026-00001 in vuln-lib==1.0.0: vuln_lib.risky is REACHABLE from main.main"},
  "locations": [{"physicalLocation": {"artifactLocation": {"uri": "vuln_lib/__init__.py", "uriBaseId": "PROJECT_ROOT"}, "region": {"startLine": 1}},
                 "logicalLocations": [{"fullyQualifiedName": "vuln_lib.risky", "kind": "function"}]}]
}
```

Rule catalog: `PYREACH-REACHABLE-CVE` (`error`), `PYREACH-POTENTIAL-CVE`
(`warning`), `PYREACH-NOT-REACHABLE-CVE` (`note`, only with `--include-all`).
Call paths ride in `codeFlows` (`entryPoint` → `call` → `vulnerableCall`).
Every output validates against OASIS SARIF v2.1.0.

JSON (`-f json`) — machine-readable summary:

```json
{"tool": "PyReach", "version": "0.1.0",
 "summary": {"total": 1, "reachable": 1, "potentially_reachable": 0, "not_reachable": 0},
 "results": [{"vulnerability": {"cveId": "CVE-2026-00001", "packageName": "vuln-lib", "installedVersion": "1.0.0", "severity": "CRITICAL"},
              "status": "REACHABLE", "path": ["main.main", "client.fetch", "vuln_lib.risky"],
              "location": {"file": "vuln_lib/__init__.py", "line": 1}}]}
```

## 7. CI integration

See `ci/README.md` (variables, emergency `--no-fail` override, cron, Docker
replica). Minimal GitLab job:

```yaml
include:
  - local: ci/gitlab/.pyreach-scan.yml

stages:
  - security
  - security_gate

pyreach_scan:
  extends: .pyreach-scan
  variables:
    PYREACH_PROJECT_PATH: "."

pyreach_gate:
  extends: .pyreach-gate
```

Jenkins: apply the `Security Scan` stage from `ci/jenkins/Jenkinsfile.pyreach`
(Warnings Next Generation plugin publishes the SARIF).

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Manifest file 'requirements.txt' not found...` | No manifest in project | Create one or pass `--manifest` |
| `OSV database not found at ...` | No local DB | Run `pyreach sync-osv` before the scan; pre-seed runner DBs |
| `No entry points detected...` | No `main` guard / framework hook found | Add `-e pkg.mod.func` or `entry_points:` in `.pyreach.yml` |
| `Unknown config key(s): ...` | Typo in `.pyreach.yml` | Fix the key (strict validation) |
| `max_depth must be in [0, 7]` | Out-of-range `-k` / config | Use 0–7 (default 5) |
| Scan > 45 s | Large tree / deep graph | `--max-depth 3`, `--exclude tests/`, more RAM |
| SARIF missing from Security tab | Runner/report configuration | Check `artifacts.reports.sarif` and the scan job; the file is also downloadable via `artifacts.paths` |
| Skipped-file warnings | Unreadable/syntax-broken `.py` | Fix or `--exclude` it (scan continues) |
| Garbled output on Windows | Console encoding | Use `-o` file output; text markers are plain ASCII |

Common mistakes: scanning the wrong directory (paths in SARIF are relative
to `PROJECT_PATH` — resolve it first); expecting findings with an empty DB
(seed/provision advisories); passing a file instead of a directory as
`PROJECT_PATH`.

## 9. Data sovereignty

Scans run fully offline: manifest parsing, SQLite lookup, AST/call-graph
analysis and serialization touch only the project directory, resolved
`site-packages`, and the local DB. Only database provisioning moves data.
Verified by static audit (S4-T7): no sockets/HTTP clients on the scan path.
