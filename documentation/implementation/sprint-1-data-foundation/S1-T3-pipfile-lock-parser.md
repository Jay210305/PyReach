# S1-T3 — Implement `Pipfile.lock` JSON parser

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 6 h |
| Dependencies | S1-T1 |
| Related docs | `03-technical-specifications.md` §3.1; `02-system-architecture.md` §Manifest Parser; `10-risk-and-contingency-plan.md` §3 (scope item 1) |

## Purpose

Support Pipenv-based projects by reading `Pipfile.lock`, a JSON document that pins exact
versions. This is the **first candidate for scope cutting** (see risks), so it must be built
behind the same interface and be fully removable without touching other modules.

## Preconditions

- S1-T1 merged.
- Sample `Pipfile.lock` fixtures available under `tests/fixtures/manifests/`.
- Understand the `Pipfile.lock` structure: top-level `default` and `develop` maps, each entry
  has a `version` like `"==2.31.0"` and optional `markers`/`extras`.

## Essential Sub-tasks

### 3.1 Write failing tests (1.0 h)

Create `tests/unit/parsers/test_manifest_pipfile.py` with 10 cases:

| Test | Fixture / Input | Expectation |
|------|-----------------|-------------|
| `test_parse_default_section` | lock with `default` | one `Dependency` per package |
| `test_parse_develop_excluded_by_default` | `develop` section | not returned unless `include_dev=True` |
| `test_parse_develop_included` | `include_dev=True` | dev deps returned |
| `test_version_operator_stripped` | `"==2.31.0"` | `version="2.31.0"` |
| `test_marker_preserved` | `"markers": "python_version >= '3.10'"` | `marker` populated |
| `test_extras_preserved` | `"extras": ["security"]` | `extra="security"` |
| `test_file_not_found` | missing path | `ConfigError` |
| `test_invalid_json` | `{not json` | `ParseError` |
| `test_missing_default_section` | `{}` | empty list (not an error) |
| `test_source_field` | any | `source="Pipfile.lock"` |

### 3.2 Implement JSON loading with validation (1.0 h)

- `json.loads(path.read_text(encoding="utf-8"))`.
- Catch `json.JSONDecodeError` -> raise `ParseError` with file + line.
- Verify the top-level value is a `dict`; if not -> `ParseError`.
- Treat missing `default`/`develop` keys as empty dicts (do not fail).

### 3.3 Implement package entry mapping (1.5 h)

For each `(pkg_name, metadata)` in selected sections:

- `name = normalize_name(pkg_name)`.
- Raw `version` is usually `"==2.31.0"`; strip any leading operator
  (`==`, `>=`, `~=`); if absent keep `""`.
- `extra`: join the `extras` list with `,` (mirror S1-T2 convention) or `None`.
- `marker`: copy `metadata.get("markers")`.
- Skip entries whose value is not a dict or that look like path/VCS references
  (e.g. `{"path": "."}` or `{"git": "..."}`) — flag as non-PyPI.

### 3.4 Implement `PipfileLockParser` class (1.0 h)

```python
class PipfileLockParser:
    source_name = "Pipfile.lock"
    def __init__(self, include_dev: bool = False, include_non_pypi: bool = False) -> None: ...
    def supports(self, path: Path) -> bool:
        return path.name == "Pipfile.lock"
    def parse(self, path: Path) -> list[Dependency]: ...
```

- Deterministic order: sort package names alphabetically within each section.
- Default section first, then (optional) develop.

### 3.5 Graceful fallback behavior (0.5 h)

- If the caller asks for `requirements.txt` and it is missing but `Pipfile.lock` exists, the
  CLI (S4-T3) may select this parser. Provide a module-level helper
  `select_manifest_parser(project_root: Path) -> ManifestParser | None` that:
  1. prefers `requirements.txt`, 2. falls back to `Pipfile.lock`, 3. returns `None`.
- This helper lives here but is consumed by the CLI.

### 3.6 Coverage and cleanup (1.0 h)

- Add fixture `sample_pipfile_lock` to `tests/unit/parsers/conftest.py`.
- Ensure `>=90%` coverage on the Pipfile-specific code paths.

## Deliverables

- `pyreach/parsers/manifest.py` — `PipfileLockParser` + `select_manifest_parser`.
- `tests/unit/parsers/test_manifest_pipfile.py`.
- Fixture `tests/fixtures/manifests/Pipfile.lock` and a minimal variant.

## Acceptance Criteria

- Passes 10 unit test cases; falls back gracefully if file missing. ✅ (roadmap S1-T3)
- Invalid JSON -> `ParseError`; missing file -> `ConfigError`.
- Non-PyPI entries (path/git) are skipped unless explicitly requested.

## Verification

```bash
uv run pytest tests/unit/parsers/test_manifest_pipfile.py -q
uv run pytest tests/unit/parsers --cov=pyreach.parsers --cov-report=term-missing
```

## Edge Cases & Pitfalls

- `version` may be omitted for VCS/path deps -> treat as non-PyPI.
- `default` entries may include `index` overrides; ignore them.
- Some locks contain `_meta` with `hash` — skip non-package top-level keys.
- Marker strings use single quotes inside JSON strings; do not attempt to normalize them.

## Risks / Scope Cuts

- **Scope cut #1** (`10-risk-and-contingency-plan.md` §3): if Sprint 1 slips >3 days, drop
  this task entirely. Because it is isolated behind `select_manifest_parser`, removal is a
  one-line change in the CLI. Mark the module section as `[NEGOTIABLE]` in code docstrings.

## Definition of Done

- [ ] Parser merged with 10+ tests green.
- [ ] `select_manifest_parser` consumed by CLI in a later sprint (leave TODO-free note in docs).
- [ ] Coverage >=90% on Pipfile paths.
- [ ] Documented as the designated scope-cut candidate.
