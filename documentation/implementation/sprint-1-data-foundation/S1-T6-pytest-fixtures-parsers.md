# S1-T6 — Write pytest fixtures and parametrized parser tests

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 6 h |
| Dependencies | S1-T2, S1-T3, S1-T5 |
| Related docs | `08-testing-strategy.md` §3, §4.1, §7, §8; `10-risk-and-contingency-plan.md` §6 |

## Purpose

Consolidate test infrastructure so parser/importer code reaches the required coverage and
every later sprint inherits reusable fixtures. This task is deliberately lightweight on new
production code and heavy on **fixture design and parametrization**.

## Preconditions

- All Sprint 1 production modules exist (S1-T2/T3/T5 merged).
- `pytest`, `pytest-cov`, `pytest-xdist` installed.

## Essential Sub-tasks

### 6.1 Build `tests/conftest.py` shared fixtures (1.5 h)

Create fixtures usable across sprints:

| Fixture | Scope | Returns |
|---------|-------|---------|
| `project_root` | function | `tmp_path` acting as a project dir |
| `sample_requirements_txt` | function | path to a written requirements file |
| `sample_pipfile_lock` | function | path to a written lock file |
| `sample_osv_record` | function | dict of one valid PyPI OSV record |
| `sample_osv_jsonl` | function | path to a 5-record JSONL file |
| `sqlite_db` | function | initialized temp DB path + connection factory |
| `reset_logging` | autouse | ensures log capture isolation |

Guidelines:
- Use `tmp_path` (function scope) for all filesystem fixtures — no shared global state.
- Fixtures must not require the full OSV dump or network.
- Provide fixture factories (`make_requirements(lines)`) instead of many near-duplicate
  fixtures when tests need variations.

### 6.2 Parametrize the manifest parser tests (1.5 h)

Refactor `test_manifest_requirements.py` and `test_manifest_pipfile.py` to use
`@pytest.mark.parametrize` with `(input_line, expected_dependency)` tuples. Cover at minimum:

- simple pin, spaces around operator, `>=`, `~=`, `<` only, extras, multiple extras,
  markers, editable, comment, blank, continuation, index-url, hash, duplicate, URL wheel,
  normalized name.
- Pipfile: default vs develop, operator stripping, markers, extras, malformed JSON,
  missing sections.

This turns the roadmap's "20 + 10 cases" into explicit, named parameters.

### 6.3 Build synthetic manifest fixtures on disk (1.0 h)

Add files under `tests/fixtures/manifests/`:

- `requirements_simple.txt`
- `requirements_complex.txt` (extras, markers, editable, comments, continuation)
- `requirements_empty.txt`
- `Pipfile.lock` (realistic, with `default` and `develop`)
- `Pipfile.malformed.lock`

Tests read these _and_ write inline variants to prove both paths.

### 6.4 Add coverage enforcement config (0.5 h)

In `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = "--cov=pyreach --cov-report=term-missing --cov-report=xml"
markers = ["performance: long-running performance tests"]
```

Set the global `--cov-fail-under=80` (see `08-testing-strategy.md` §7). Per-module thresholds
(`parsers>=90`) are checked explicitly in a separate coverage test or CI step.

### 6.5 Add edge-case and regression tests (1.0 h)

- UTF-8 BOM requirements file.
- CRLF line endings.
- Requirements referencing a local `.whl` path.
- OSV record with `aliases: null` and with `severity: []`.
- Empty JSONL file -> zero stats, no error.
- Importer re-run idempotency (already in S1-T5; ensure parametrized here if needed).

### 6.6 Verify coverage thresholds (0.5 h)

Run coverage and confirm:
- `pyreach/parsers/` >= 90%
- `pyreach/osv/` >= 80%
- overall >= 80%

If any file is below, add targeted tests rather than excluding lines. Document unavoidable
platform-specific branches with `# pragma: no cover` and a justification.

## Deliverables

- `tests/conftest.py` with shared fixtures + factories.
- Parametrized/refactored parser tests.
- `tests/fixtures/manifests/` fixture files.
- Updated `pyproject.toml` pytest config.
- Coverage report (CI artifact in S1-T7).

## Acceptance Criteria

- >=80% branch coverage on parsers; all tests green. ✅ (roadmap S1-T6)
- Fixtures are reusable by Sprints 2-4 (documented in `conftest.py` docstring).
- No test depends on network or the real OSV dump.

## Verification

```bash
poetry run pytest --cov=pyreach --cov-report=term-missing
poetry run pytest tests/unit/parsers -q -n auto
```

## Edge Cases & Pitfalls

- Don't over-mock: parsers are pure, so test real files on `tmp_path`.
- Avoid fixture scope creep (`session`-scoped mutable fixtures cause cross-test pollution).
- `--cov-fail-under` in `addopts` will make the 10k performance test count unless deselecting;
  keep performance marker excluded from default runs (`-m "not performance"`).

## Risks / Scope Cuts

- **R6 (academic overload)**: if time is short, reduce per-module coverage targets to 80%
  project-wide only with advisor approval (`10-risk-and-contingency-plan.md` §3, §6).

## Definition of Done

- [ ] Shared fixtures merged and documented.
- [ ] Parametrized suites cover roadmap edge cases.
- [ ] Coverage thresholds met and reproducible locally.
- [ ] `pyproject.toml` pytest config committed.
