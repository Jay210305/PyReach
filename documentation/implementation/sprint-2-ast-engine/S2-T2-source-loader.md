# S2-T2 — Implement `SourceLoader` with ignore pattern support

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 4 h |
| Dependencies | S2-T1 (recommended), S1-T1 (exceptions) |
| Related docs | `02-system-architecture.md` §Source Code Loader; `03-technical-specifications.md` §2, §5 (ignore_paths) |

## Purpose

Provide a deterministic, safe iterator over the Python source files that need analysis,
excluding virtualenvs, caches, and user-configured paths. Every downstream AST task consumes
this module, so its discovery rules must be explicit and testable.

## Preconditions

- Package `pyreach/loaders/__init__.py` exists.
- `ConfigError`/`ParseError` available.
- Test fixtures with nested directories under `tests/fixtures/projects/`.

## Essential Sub-tasks

### 2.1 Define the `SourceFile` record and loader API (0.5 h)

In `pyreach/loaders/source.py`:

```python
@dataclass(frozen=True)
class SourceFile:
    path: Path          # absolute
    rel_path: Path      # relative to project root (for SARIF URIs)

class SourceLoader:
    def __init__(self, root: Path, ignore_patterns: list[str] | None = None) -> None: ...
    def discover(self) -> list[SourceFile]: ...
    def read(self, sf: SourceFile) -> str: ...
```

- `discover()` returns a deterministically sorted list.
- `read()` opens with `encoding="utf-8"`; raises `ParseError` on `UnicodeDecodeError`.

### 2.2 Implement directory walking with exclusions (1.5 h)

- Use `Path.rglob("*.py")` from the project root.
- Always exclude, by default:
  `**/venv/**`, `**/.venv/**`, `**/.tox/**`, `**/__pycache__/**`, `**/node_modules/**`,
  `**/.git/**`, `**/build/**`, `**/dist/**`, `**/.mypy_cache/**`, `**/.pytest_cache/**`.
- Apply user `ignore_patterns` via `pathlib.PurePath.match` / `fnmatch` semantics relative to
  root (patterns like `tests/`, `docs/`).
- Never follow symlinks outside the root (`resolve()` each path and verify it is under root);
  reject `..` traversal (spec §Security).

### 2.3 Implement ignore-pattern normalization (0.75 h)

- Accept both `"tests/"` and `"tests"`; treat directory patterns as prefix matches.
- Accept glob patterns (`"**/migrations/*.py"`).
- Merge defaults + user patterns without duplication.
- Document precedence: user patterns cannot re-include default-excluded directories.

### 2.4 Write tests (1.25 h)

Create `tests/unit/loaders/test_source.py`:

| Test | Assertion |
|------|-----------|
| `test_discovers_py_files` | all expected `.py` files returned |
| `test_excludes_venv` | files under `venv/` absent |
| `test_excludes_pycache` | `__pycache__` absent |
| `test_user_ignore_pattern` | `tests/` excluded when configured |
| `test_glob_ignore_pattern` | `**/migrations/*.py` excluded |
| `test_deterministic_order` | two calls return identical order |
| `test_rel_path` | `rel_path` is relative to root |
| `test_path_traversal_rejected` | symlink/`..` outside root rejected or skipped |
| `test_non_utf8_file_raises_parse_error` | `read()` raises `ParseError` |
| `test_empty_project` | no `.py` files -> empty list |

Build a synthetic tree with `tmp_path`: `venv/x.py`, `pkg/a.py`, `pkg/__pycache__/b.py`,
`tests/test_x.py`, `pkg/migrations/001.py`.

## Deliverables

- `pyreach/loaders/source.py`
- `tests/unit/loaders/test_source.py`

## Acceptance Criteria

- Discovers all `.py` files excluding `venv/`, `__pycache__/`. ✅ (roadmap S2-T2)
- User ignore patterns honored; deterministic ordering.
- Reads confined to the project root.

## Verification

```bash
poetry run pytest tests/unit/loaders/test_source.py -q
poetry run pytest tests/unit/loaders --cov=pyreach.loaders --cov-report=term-missing
```

## Edge Cases & Pitfalls

- `rglob` on Windows may be slow on huge trees; acceptable for target project sizes.
- Hidden directories (`.venv`) are easy to miss — include them in defaults explicitly.
- A file may exist but be unreadable (permissions); catch `OSError` -> `ParseError` with path.
- Case-insensitive filesystems: avoid duplicate discovery via `resolve()` de-duplication.

## Risks / Scope Cuts

- If symlink handling proves complex, disable symlink following entirely and document it; this
  is safer and still correct for the target projects.

## Definition of Done

- [ ] Loader + tests merged.
- [ ] Defaults and merge rules documented in docstrings.
- [ ] Coverage >=85% on `loaders/`.
