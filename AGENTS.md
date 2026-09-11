# AGENTS.md — PyReach Project Specification & Agent Guide

This is the single operational reference for contributors and AI coding agents working in the
PyReach repository. It consolidates the specifications spread across `documentation/` (01-10)
and the detailed task breakdown under `documentation/implementation/`.

If anything here conflicts with `documentation/`, the numbered specification documents are the
source of truth and this file should be corrected.

---

## 1. What PyReach Is

PyReach is a **local-first, static reachability analyzer for Python dependency
vulnerabilities**. Given a Python project's manifest and source, it:

1. Parses installed dependencies (`requirements.txt`, `Pipfile.lock`).
2. Looks up known advisories in a local SQLite OSV database.
3. Builds an interprocedural call graph with NetworkX.
4. Determines whether each vulnerable symbol is actually reachable from an application entry
   point.
5. Emits a **SARIF v2.1.0** report and an exit code suitable for CI gating.

Non-negotiables:
- **Local-first**: no network during analysis (only `pyreach sync-osv` may fetch data).
- **Zero critical false negatives**: uncertainty resolves upward to `POTENTIALLY_REACHABLE`.
- **<45s** scan budget for typical microservices.
- **SARIF v2.1.0** output for GitLab/GitHub/VS Code consumption.

---

## 2. Environment & Tooling — uv (MANDATORY)

PyReach uses **[uv](https://docs.astral.sh/uv/)** as its single dependency/environment manager
and a project-local `.venv`. Poetry is **no longer used**.

- `uv` version: `>=0.5` (bootstrapped with 0.12.6).
- Interpreter: `requires-python = ">=3.10"`; the checked-in dev `.venv` runs Python 3.14.
- `uv.lock` is **committed**; CI installs with `uv sync --locked`.
- `[tool.uv] package = false` until the `pyreach/` package exists (then flip to `true` and add
  the `[build-system]` from the spec).

### Golden commands

```powershell
uv sync                       # create/update .venv from uv.lock (runtime + dev)
uv sync --no-dev              # runtime only (CI scan stage)
uv sync --locked              # CI: fail if pyproject.toml and uv.lock drift
uv run pytest                 # run inside .venv, no activation needed
uv run ruff check .           # lint
uv run ruff format .           # format (or: uv run black .)
uv run mypy pyreach           # type-check
uv add <package>              # add runtime dep (updates pyproject + lock)
uv add --dev <package>        # add dev dep
uv remove <package>
uv lock                       # re-lock after manual pyproject edits
uv build                      # build wheel + sdist (once package exists)
```

Activation is optional:

```powershell
.\.venv\Scripts\Activate.ps1       # Windows PowerShell
source .venv/bin/activate          # POSIX
```

**Never** `pip install` into `.venv`; that desynchronizes it from `uv.lock`. Use `uv add`.

---

## 3. Allocated Dependencies

Declared in root `pyproject.toml` and locked in `uv.lock` (34 packages installed).

**Runtime** (`[project].dependencies`)

| Package | Constraint | Used by |
|---------|-----------|---------|
| `networkx` | `>=3.0` | call graph `DiGraph` (Sprint 3) |
| `jsonschema` | `>=4.0` | SARIF v2.1.0 validation (Sprint 4) |
| `packaging` | `>=23.0` | manifest parsing + version ranges (Sprint 1) |
| `pyyaml` | `>=6.0` | `.pyreach.yml` loader (S4-T5) |

**Dev** (`[dependency-groups].dev`)

| Package | Constraint | Purpose |
|---------|-----------|---------|
| `pytest` | `>=7.0` | test runner |
| `pytest-cov` | `>=4.0` | coverage |
| `pytest-xdist` | `>=3.0` | parallel tests |
| `factory-boy` | `>=3.3` | test data generation |
| `freezegun` | `>=1.0` | time mocking |
| `black` | `>=23.0` | formatter |
| `mypy` | `>=1.0` | static typing |
| `ruff` | `>=0.1.0` | linter |

Standard library only for: `ast`, `sqlite3`, `argparse`, `json`, `importlib.metadata`,
`contextlib`, `collections`. Do **not** add a CLI framework (Click/Typer); argparse is the
chosen design.

---

## 4. Repository Layout

```
PyReach/
├── AGENTS.md                      <- this file
├── pyproject.toml                 <- project + tool config (uv)
├── uv.lock                        <- committed lockfile
├── .venv/                         <- local env (git-ignored)
├── .gitignore
├── documentation/
│   ├── 01-project-overview.md
│   ├── 02-system-architecture.md
│   ├── 03-technical-specifications.md
│   ├── 04-implementation-roadmap.md
│   ├── 05-data-model-and-storage.md
│   ├── 06-ast-and-callgraph-engine.md
│   ├── 07-sarif-and-cli-design.md
│   ├── 08-testing-strategy.md
│   ├── 09-cicd-integration.md
│   ├── 10-risk-and-contingency-plan.md
│   └── implementation/            <- decomposed tasks (S1-T0 … S4-T8)
└── pyreach/                       <- (NOT YET CREATED) source package
```

Target package structure (from `03-technical-specifications.md` §2):

```
pyreach/
├── __init__.py
├── cli.py
├── config.py
├── exceptions.py
├── logger.py
├── parsers/{__init__,manifest,osv_json}.py
├── loaders/{__init__,source,packages}.py
├── osv/{__init__,mapper,importer}.py
├── ast/{__init__,builder,symbols,resolver}.py
├── callgraph/{__init__,engine,nodes,edges}.py
├── reachability/{__init__,analyzer,classifier,entrypoints}.py
├── output/{__init__,sarif,summary}.py
└── db/{__init__,connection,schema.sql,migrations/}
```

---

## 5. Architecture (summary)

```
Input Layer            Analysis Core                    Output Layer
-----------            -------------                    ------------
requirements.txt  ->   Manifest Parser              ->  SARIF v2.1.0 Serializer
Pipfile.lock           OSV Mapper                       CLI Reporter
Source code            AST Builder                      Exit Code Controller
site-packages          Call Graph Engine (NetworkX)
                       Reachability Analyzer
        |                       |                                |
        v                       v                                v
   OSV JSON dump          SQLite (advisories,            GitLab CI / local IDE
   (offline)              cg_nodes/edges, cache)
```

Pipeline:
1. Parse manifest -> `list[Dependency]`.
2. Query OSV SQLite -> `list[Vulnerability]` (affected symbols).
3. Parse sources -> `ModuleAST` + symbol tables.
4. Resolve installed packages -> site-packages paths.
5. Build `networkx.DiGraph` of nodes/edges.
6. Detect entry points; run bounded reachability + classify.
7. Serialize SARIF/JSON/text; return exit code.

Key decisions: local-first, SQLite storage, `DiGraph` (not `MultiDiGraph`), bounded DFS/BFS
with `k=5`, conservative over-approximation for dynamic constructs.

---

## 6. Data Contracts

```python
@dataclass(frozen=True)
class Dependency:            # parsers/manifest.py
    name: str; version: str; source: str
    extra: str | None = None; marker: str | None = None

@dataclass
class ModuleAST:             # ast/builder.py
    file_path: str; module_fqn: str; tree: ast.AST
    symbol_table: dict[str, str]; imports: dict[str, str]

@dataclass(frozen=True)
class CGNode:                # callgraph/nodes.py
    fqn: str; file_path: str | None; line_number: int | None
    node_type: Literal["FUNCTION","METHOD","CLASS","LAMBDA"]

@dataclass(frozen=True)
class CGEdge:                # callgraph/edges.py
    caller: CGNode; callee: CGNode
    edge_type: Literal["STATIC","DYNAMIC","INHERITANCE","IMPORT"]
    confidence: float = 1.0

@dataclass
class Vulnerability:         # osv/mapper.py
    osv_id: str; cve_id: str | None; package_name: str
    severity_score: float | None; severity_level: str | None
    summary: str; affected_symbols: list[str]
    version_introduced: str | None; version_fixed: str | None

@dataclass
class ReachabilityResult:    # reachability/analyzer.py
    vulnerability: Vulnerability
    status: Literal["REACHABLE","NOT_REACHABLE","POTENTIALLY_REACHABLE"]
    entry_points_reached: list[str]; paths: list[list[str]]; reasoning: str
```

Name normalization is PEP 503: lowercase; runs of `-_.` collapse to `-`.

---

## 7. CLI Specification

```
pyreach [OPTIONS] <PROJECT_PATH>
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--manifest` | `-m` | `requirements.txt` | dependency manifest |
| `--db-path` | `-d` | `~/.pyreach/osv.db` | OSV SQLite DB |
| `--output` | `-o` | `pyreach-results.sarif` | output file |
| `--entry-point` | `-e` | auto | entry point FQN (repeatable) |
| `--max-depth` | `-k` | `5` | traversal depth (never >7) |
| `--include-potentially` | | off | treat potential as failure |
| `--include-all` | | off | include NOT_REACHABLE in output |
| `--no-fail` | | off | always exit 0 on findings |
| `--format` | `-f` | `sarif` | `sarif` \| `json` \| `text` |
| `--exclude` | | `[]` | path pattern to exclude (repeatable) |
| `--cache` | | on | use call graph cache if available |
| `--verbose` | `-v` | off | DEBUG logging |
| `--quiet` | `-q` | off | suppress non-error output |
| `--version` / `--help` | | | info and exit |

**Exit codes**: `0` success/no reachable (or `--no-fail`); `1` reachable (or potentially
reachable with `--include-potentially`); `2` configuration/runtime error.

Subcommand `pyreach sync-osv [--db-path] [--source] [--incremental]` populates the DB.

---

## 8. Configuration (`.pyreach.yml`)

```yaml
pyreach:
  version: "1"
  entry_points: ["myapp.cli:main", "myapp.api:init_routes"]
  ignore_paths: ["tests/", "docs/", "scripts/"]
  max_depth: 5
  manifest: "requirements.txt"
  osv_db: "~/.pyreach/osv.db"
  thresholds:
    fail_on_reachable: true
    fail_on_potentially: false
```

**Precedence** (highest first): CLI flags -> project `.pyreach.yml` -> user-global
`~/.pyreach/config.yml` -> built-in defaults.

---

## 9. SARIF Output

- Document: `$schema`, `version: "2.1.0"`, one `run`.
- Rules: `PYREACH-REACHABLE-CVE` (`error`), `PYREACH-POTENTIAL-CVE` (`warning`),
  `PYREACH-NOT-REACHABLE-CVE` (`note`, only with `--include-all`).
- Reachable paths -> `result.codeFlows[].threadFlows[].locations[]` with kinds
  `entryPoint` -> `call` -> `vulnerableCall`.
- All custom metadata lives only in `result.properties` (never new top-level fields).
- `originalUriBaseIds.PROJECT_ROOT` + relative `artifactLocation.uri` (forward slashes).
- Every output MUST validate against the cached OASIS schema in tests.

---

## 10. Testing & Quality Gates

- **TDD is mandatory**: write the failing test first; the test name is the spec.
- Pyramid: ~80% unit, ~15% integration, ~5% E2E.
- Framework: pytest (+ pytest-cov, pytest-xdist); fixtures under `tests/fixtures/`.
- Coverage: overall `>=80%`; `parsers/ >=90%`; `ast/`, `callgraph/`, `reachability/ >=85%`;
  `output/sarif.py >=80%`.

```powershell
uv run pytest -m "not performance" --cov=pyreach --cov-report=term-missing --cov-report=xml
uv run pytest tests/unit/parsers -q -n auto
uv run pytest -m performance -q
```

- No test may depend on the network or the full OSV dump; use fixtures/stub advisories.
- Performance tests are marked `performance` and excluded from default runs.
- Every bug fix ships a regression test.

---

## 11. Coding Conventions

- Python 3.10+ compatible (avoid 3.11+ only syntax even though the dev env is 3.14).
- Full type hints on public functions; `mypy` clean (`disallow_untyped_defs = true`).
- `ruff` clean; line length 100; formatting via `black`.
- **Do not add comments** unless a non-obvious algorithm demands one; prefer docstrings.
- Dataclasses for data contracts; `frozen=True` for immutable value objects.
- No `eval`/`exec` of external input (manifests, source). Parse, never execute.
- Confine file reads to the project root and resolved site-packages; reject `..` traversal.
- Prefer iterative traversal over recursion (Python recursion limit).
- Conventional commits referencing task IDs (`S1-T2: ...`); one task per commit/MR.

---

## 12. Error Handling

```
PyReachError
├── ConfigError    # bad .pyreach.yml, missing manifest
├── ParseError     # malformed manifest / invalid Python syntax
├── OSVError       # missing/corrupt OSV DB
├── AnalysisError  # AST or call graph failure
└── OutputError    # SARIF serialization / write failure
```

- A `ParseError` on a single source file -> WARNING, skip file, continue (never exit 2).
- Missing OSV DB -> exit 2, instruct `pyreach sync-osv`.
- No entry points -> exit 2, suggest `-e`.
- `MemoryError` -> exit 2, advise `--max-depth` reduction / `--exclude`.
- Tracebacks hidden unless `--verbose`.

---

## 13. Implementation Roadmap

Phase 2 = 4 biweekly sprints, 240 person-hours. Detailed sub-tasks live in
`documentation/implementation/`.

| Sprint | Weeks | Owner | Effort | Goal | Milestone |
|--------|-------|-------|--------|------|-----------|
| 1 | 5-6 | Julio | 40 h | Manifest parsing, OSV ingestion, TDD fixtures | M1 Data Foundation |
| 2 | 7-8 | Julio | 45 h | AST engine + alias resolution | M2 Code Comprehension |
| 3 | 9-10 | Alonso | 45 h | Call graph + reachability | M3 Analysis Core |
| 4 | 11-12 | Alonso | 42 h | SARIF, CLI, CI/CD gates | M4 Product Delivery |

Dependencies:

```
Sprint 1 (Parser/OSV) ---+
                         +--> Sprint 3 (Call Graph/Reachability) --> Sprint 4 (SARIF/CLI)
Sprint 2 (AST Engine) ---+
```

**Critical path**: S1 -> S3 -> S4. Sprint 2 must complete before Sprint 3 starts.
Task IDs: `S1-T0 … S4-T8`. `S1-T0` (uv bootstrap) is a hard prerequisite for all tasks.

### Scope negotiation (when a sprint slips >3 days)
1. Drop `Pipfile.lock` support (S1-T3).
2. Skip star-import resolution (S2-T5).
3. Postpone `.pyreach.yml` (S4-T5).
4. Reduce `--max-depth` default 5 -> 3 (S3-T5).
5. Postpone SQLite call-graph caching.

---

## 14. CI/CD

- Local test gate: `.gitlab-ci.yml` runs `uv sync --locked` + `uv run pytest` on every push;
  failing tests block merges.
- Security stage (Sprint 4): runs `pyreach` with `--format sarif --include-potentially`,
  publishes `artifacts.reports.dependency_scanning`, and gates on the exit code.
- OSV DB is pre-seeded at `/opt/pyreach/osv.db` and refreshed weekly by cron
  (`pyreach sync-osv --incremental`).
- Runner: Lidercom on-prem, no cloud egress; Docker replica is the contingency target.

---

## 15. Risk Register (headline)

| ID | Risk | Mitigation |
|----|------|-----------|
| R1 | Graph combinatorial explosion | `max_depth=5`, `DiGraph`, lazy library loading, pruning |
| R2 | False negatives from metaprogramming | DYNAMIC edges -> always `POTENTIALLY_REACHABLE` |
| R3 | SARIF schema rejection | jsonschema validation from day one; extras only in `properties` |
| R4 | Lidercom access delay | containerized replicas + public analogues |
| R5 | Sponsor deprioritization | biweekly demos; synthetic data suffices academically |
| R6 | Academic overload | 3-day buffer/sprint; front-load heavy tasks |
| R7 | AST complexity slippage | M1 self-study (S2-T1); simplify imports if needed |

---

## 16. Documentation Map

| Document | Contents |
|----------|----------|
| `documentation/01-project-overview.md` | problem, objectives, scope, stakeholders |
| `documentation/02-system-architecture.md` | components, data flow, deployment, tech stack |
| `documentation/03-technical-specifications.md` | environment, package layout, contracts, CLI |
| `documentation/04-implementation-roadmap.md` | sprints, tasks, milestones, buffer |
| `documentation/05-data-model-and-storage.md` | SQLite DDL, ingestion, caching |
| `documentation/06-ast-and-callgraph-engine.md` | AST pipeline, graph algorithms, heuristics |
| `documentation/07-sarif-and-cli-design.md` | SARIF structure, CLI UX, error messages |
| `documentation/08-testing-strategy.md` | test pyramid, fixtures, coverage |
| `documentation/09-cicd-integration.md` | GitLab/Jenkins, runner setup, quality gates |
| `documentation/10-risk-and-contingency-plan.md` | risk responses, scope protocol |
| `documentation/implementation/` | per-task decomposition with sub-tasks + DoD |

---

## 17. Current Status

- [x] Documentation phase complete (docs 01-10).
- [x] Task decomposition complete (`documentation/implementation/`, S1-T0 … S4-T8).
- [x] Environment bootstrapped with uv; all dependencies allocated in `.venv`.
- [x] `pyproject.toml`, `uv.lock`, `.gitignore`, `AGENTS.md` created.
- [ ] `pyreach/` package not yet implemented — start at
      `documentation/implementation/sprint-1-data-foundation/S1-T0-environment-bootstrap-uv.md`
      then S1-T1.

When you finish a task, update its Definition of Done checklist and run the full gate:

```powershell
uv run ruff check . ; uv run mypy pyreach ; uv run pytest -m "not performance" --cov=pyreach
```
