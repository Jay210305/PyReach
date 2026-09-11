# S2-T7 — Write pytest fixtures with real-world code samples

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 6 h |
| Dependencies | S2-T2, S2-T3, S2-T4, S2-T5, S2-T6 |
| Related docs | `08-testing-strategy.md` §3, §4.2, §8; `10-risk-and-contingency-plan.md` §6 |

## Purpose

Validate the AST engine against **real Python code**, not just toy snippets, and provide the
fixture corpus that Sprint 3's call-graph tests will reuse. Coverage is the secondary goal;
realism is the primary one (roadmap DoD names requests, Flask, FastAPI stubs).

## Preconditions

- All Sprint 2 modules merged.
- `tests/fixtures/` structure from `08-testing-strategy.md` §8 exists.

## Essential Sub-tasks

### 7.1 Assemble a real-world code corpus (2 h)

Create `tests/fixtures/code_samples/` with representative files:

| Sample | Contents | Purpose |
|--------|----------|---------|
| `requests_snippet.py` | imports `requests`, defines a client class calling `requests.get` | alias/re-export resolution |
| `flask_snippet.py` | `@app.route` decorators, route handlers | entry-point detection prep |
| `fastapi_snippet.py` | `@app.get`, async handlers | async function handling |
| `relative_pkg/` | package with `__init__.py` and sibling modules using relative imports | relative import resolution |
| `star_import.py` | `from math import *` | star import handling |
| `dynamic_patterns.py` | `eval`, `exec`, `getattr`, `importlib.import_module` | dynamic edge detection prep |
| `inheritance.py` | base/derived classes with `super()` | inheritance prep |
| `syntax_error.py` | deliberately broken | graceful skip |

Guidelines:
- Keep files small (10-40 lines) and license-safe (write them ourselves, do not vendor GPL code).
- Do not depend on installing requests/flask/fastapi; the snippets are parsed, not executed.

### 7.2 Add loader/resolver fixtures (1 h)

In `tests/unit/ast/conftest.py`:

- `module_ast_factory(source: str, fqn: str)` -> builds a `ModuleAST` from a string.
- `module_index_from_dir(path)` -> builds a `ModuleIndex` from the corpus.
- `opened_project` -> copies a fixture project to `tmp_path` so tests can mutate freely.

### 7.3 Write corpus-driven tests (1.5 h)

Create `tests/unit/ast/test_real_world.py`:

| Test | Assertion |
|------|-----------|
| `test_requests_snippet_symbols` | `requests` bound; `requests.get` resolves |
| `test_flask_routes_discovered` | decorators extracted without error |
| `test_fastapi_async_handlers` | `AsyncFunctionDef` produces same structures as sync |
| `test_relative_package_imports` | sibling/parent FQNs correct |
| `test_star_import_names` | `sqrt`/`pi` present from `math` |
| `test_dynamic_patterns_detected` | calls to `eval/exec/getattr` flagged as dynamic |
| `test_inheritance_parsed` | base class name resolvable |
| `test_syntax_error_skipped` | builder returns `None`, logs warning |
| `test_no_crashes_on_corpus` | `build_all` over the whole corpus succeeds |

### 7.4 Verify coverage thresholds (1 h)

Run coverage on `pyreach/ast/` and `pyreach/loaders/`:

- Target >=85% on `ast/` and `loaders/` (roadmap: >=80% on `ast/` and `loaders/` modules).
- Fill gaps with focused unit tests rather than broad smoke tests.
- Document any `# pragma: no cover` with rationale (platform branches only).

### 7.5 Wire fixtures into `conftest.py` hierarchy (0.5 h)

- Root `tests/conftest.py` holds cross-sprint fixtures (S1-T6).
- `tests/unit/ast/conftest.py` holds AST-specific ones.
- Document in each conftest docstring which sprints consume which fixtures so Sprint 3 can
  import them without duplication.

## Deliverables

- `tests/fixtures/code_samples/` corpus.
- `tests/unit/ast/conftest.py`.
- `tests/unit/ast/test_real_world.py`.
- Coverage report showing thresholds met.

## Acceptance Criteria

- >=80% coverage on `ast/` and `loaders/` modules. ✅ (roadmap S2-T7)
- Corpus exercises absolute, relative, and star imports on realistic code.
- No test requires network access or installed third-party frameworks.

## Verification

```bash
uv run pytest tests/unit/ast tests/unit/loaders -q
uv run pytest tests/unit/ast --cov=pyreach.ast --cov-report=term-missing
uv run pytest tests/unit/loaders --cov=pyreach.loaders --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Do not commit copyrighted library source; authored snippets only.
- Keep async snippets parseable on Python 3.10 (avoid 3.11+ `TaskGroup` syntax).
- Star-importing `math` is safe because resolution is static (no import execution), but the
  fixture must not actually `import math` at runtime unless intended.
- Corpus files must not be collected by pytest as tests (name them `*_snippet.py`, never
  `test_*.py`).

## Risks / Scope Cuts

- **R7**: if corpus assembly overruns, reduce to requests/flask/relative-package samples and
  note the reduced realism.

## Definition of Done

- [ ] Corpus and tests merged.
- [ ] Coverage thresholds met on `ast/` and `loaders/`.
- [ ] Fixtures documented for Sprint 3 reuse.
- [ ] No real-world snippet execution during tests.
