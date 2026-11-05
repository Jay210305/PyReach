# PyReach

Local-first static reachability analysis for Python dependency vulnerabilities.

Given a project's manifest and source, PyReach parses dependencies,
looks up known advisories in a local SQLite OSV database, builds a call
graph, and reports whether each vulnerable symbol is actually reachable
from an application entry point — as SARIF v2.1.0, with a CI-gating exit
code. No network access during analysis.

## Install

```powershell
uv sync
```

## Scan

```powershell
uv run pyreach /path/to/project --db-path ~/.pyreach/osv.db -o results.sarif
uv run pyreach /path/to/project -f text
```

Exit codes: `0` clean (or `--no-fail`), `1` reachable findings,
`2` configuration/runtime error.

See `documentation/` for the full specification and `ci/README.md` for
CI/CD templates.

