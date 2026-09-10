# S1-T2 — Implement `requirements.txt` regex/line parser

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 8 h |
| Dependencies | S1-T1 (must be merged) |
| Related docs | `03-technical-specifications.md` §3.1, §8; `02-system-architecture.md` §Manifest Parser; `08-testing-strategy.md` §4.1 |

## Purpose

Turn a `requirements.txt` file into a normalized `list[Dependency]` that the OSV mapper can
query. This is the primary input format for Lidercom, so correctness and safety
(no `eval` of requirement lines) are critical.

## Preconditions

- S1-T1 merged: `Dependency`, `normalize_name`, `ManifestParser`, exceptions available.
- `packaging>=23.0` installed (declared in `pyproject.toml`).

## Essential Sub-tasks

### 2.1 Write failing tests first (1.5 h)

Create `tests/unit/parsers/test_manifest_requirements.py` with the roadmap's 20 cases
(spec §4.1). Use `tmp_path` fixtures. Minimum set:

| Test | Input | Expectation |
|------|-------|-------------|
| `test_parse_simple_package` | `requests==2.31.0` | `Dependency("requests","2.31.0","requirements.txt")` |
| `test_parse_pinned_with_spaces` | `requests == 2.31.0` | same as above |
| `test_parse_version_range_lower_bound` | `flask>=2.0.0` | `version="2.0.0"` |
| `test_parse_version_compatible` | `flask~=2.0.0` | `version="2.0.0"` |
| `test_parse_upper_bound_only` | `flask<3.0` | `version=""` (no lower bound) |
| `test_parse_with_extras` | `numpy[extras]>=1.24.0` | `extra="extras"`, `version="1.24.0"` |
| `test_parse_multiple_extras` | `uvicorn[standard,reload]` | `extra="standard,reload"` |
| `test_parse_with_marker` | `x==1; python_version >= "3.10"` | `marker='python_version >= "3.10"'` |
| `test_parse_editable_install_flagged` | `-e git+https://...` | returned only if `include_non_pypi=True`, else skipped |
| `test_parse_comment_ignored` | `# comment` | not present |
| `test_parse_inline_comment` | `requests==2.31.0  # pin` | parsed without comment |
| `test_parse_empty_lines` | `\n\n` | ignored |
| `test_parse_file_not_found` | missing path | `ConfigError` |
| `test_parse_malformed_line` | `===bad===` | `ParseError` (or skipped with warning; pick one and document) |
| `test_parse_hash_option` | `--hash=sha256:...` | ignored / attached |
| `test_parse_line_continuation` | backslash continuation | joined correctly |
| `test_parse_index_url_skipped` | `--index-url ...` | skipped |
| `test_parse_duplicate_keeps_last` | two entries | last wins |
| `test_parse_url_requirement` | `https://.../pkg.whl` | flagged non-PyPI |
| `test_normalization_applied` | `Foo_Bar==1.0` | `name="foo-bar"` |

### 2.2 Implement line reader and continuation handling (1.0 h)

- Open with `encoding="utf-8"`; tolerate BOM (`utf-8-sig`).
- Join logical lines: a trailing `\` continues to the next physical line.
- Strip inline comments: split on ` #` (whitespace before `#`) so URLs containing `#egg=`
  are preserved (e.g. `-e git+...#egg=x`).
- Ignore blank lines and lines starting with `#`.

### 2.3 Implement parsing of each logical line using `packaging` (2.5 h)

Use `packaging.requirements.Requirement` as the primary parser (spec forbids `eval`):

```python
from packaging.requirements import Requirement, InvalidRequirement
```

- On success: extract `req.name`, `req.extras`, `req.marker`, `req.specifier`.
- Derive `version` from the specifier:
  1. Find an `==` entry -> that exact version.
  2. Else find the first `>=` or `~=` entry -> that lower bound.
  3. Else `""`.
- Normalize `name` via `normalize_name`.
- On `InvalidRequirement`: handle special leading tokens first (`-e`, `--`, `-r`, URL wheels)
  before declaring malformed.

### 2.4 Implement non-PyPI / option handling (1.5 h)

Classify leading tokens:

| Prefix | Handling |
|--------|----------|
| `-e ` or `--editable` | editable install; if VCS URL -> non-PyPI, skip unless `include_non_pypi` |
| `-r ` / `--requirement` | nested file; either recurse (bounded depth) or skip with warning — document choice |
| `--index-url`, `--extra-index-url`, `--find-links`, `--trusted-host` | skip |
| `--hash=` | ignore (may appear after a continuation) |
| bare URL / path ending `.whl`/`.tar.gz` | non-PyPI, flag |
| `-c ` / `--constraint` | skip (out of scope) |

Add constructor flag `include_non_pypi: bool = False` on the parser class.

### 2.5 Implement the `RequirementsTxtParser` class (1.0 h)

```python
class RequirementsTxtParser:
    source_name = "requirements.txt"
    def __init__(self, include_non_pypi: bool = False) -> None: ...
    def supports(self, path: Path) -> bool:
        return path.name == "requirements.txt"
    def parse(self, path: Path) -> list[Dependency]: ...
```

- Missing file -> `ConfigError` with the path in the message.
- Return a deterministically ordered list (preserve file order; drop duplicates keeping last).

### 2.6 Backfill tests and reach coverage (1.0 h)

- Add parametrized tests for the 20 cases if not already parametrized.
- Run coverage; ensure `>=90%` on `parsers/manifest.py` (critical module target).

## Deliverables

- `pyreach/parsers/manifest.py` — `RequirementsTxtParser`.
- `tests/unit/parsers/test_manifest_requirements.py`.
- Test fixtures (if not already in `conftest.py`): `sample_requirements_txt`.

## Acceptance Criteria

- Passes 20 unit test cases including extras, markers, editable installs. ✅ (roadmap S1-T2)
- No use of `eval`/`exec`; parsing delegated to `packaging`.
- `ConfigError` on missing file; `ParseError` only on truly malformed lines.
- Coverage >=90% on the parser module.

## Verification

```bash
poetry run pytest tests/unit/parsers/test_manifest_requirements.py -q
poetry run pytest tests/unit/parsers --cov=pyreach.parsers --cov-report=term-missing
poetry run ruff check pyreach/parsers/manifest.py
```

## Edge Cases & Pitfalls

- URLs contain `#egg=`; naive `split("#")` comment stripping would corrupt them.
- Environment markers contain quoted commas/operators — let `packaging` handle them.
- `~=` is a compatible-release operator; treat its value as the lower bound only.
- Windows line endings (`\r\n`) must be stripped.
- A requirement may combine extras **and** markers: `pkg[extra]; python_version < "3.11"`.

## Risks / Scope Cuts

- **Scope item 1 (lowest value)**: `Pipfile.lock` support can be dropped — but this task is
  `requirements.txt`, which is never cut.
- If nested `-r` recursion proves complex, skip with a warning (documented) rather than recurse.

## Definition of Done

- [ ] `RequirementsTxtParser` merged; 20+ tests green.
- [ ] Coverage >=90% on `parsers/manifest.py`.
- [ ] `ruff`/`mypy` clean.
- [ ] No dynamic execution anywhere in the parser.
