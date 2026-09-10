# S2-T4 — Implement `ASTBuilder`: parse files, compute module FQN, wrap in `ModuleAST`

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 8 h |
| Dependencies | S2-T1, S2-T2 |
| Related docs | `06-ast-and-callgraph-engine.md` §1.1, §1.2; `03-technical-specifications.md` §3.2; spec §8 (error handling) |

## Purpose

Produce the canonical `ModuleAST` object—parsed tree + metadata + module FQN—for every source
file. This is the interface between file discovery and symbol/call-graph construction.

## Preconditions

- S2-T1 notes available (FQN algorithm validated).
- S2-T2 `SourceLoader` merged.
- `ast` stdlib; `ParseError` available.

## Essential Sub-tasks

### 4.1 Implement `parse_source` (1 h)

In `pyreach/ast/builder.py`:

```python
def parse_source(file_path: str, source_text: str) -> ast.AST:
    try:
        return ast.parse(source_text, filename=file_path, mode="exec")
    except SyntaxError as exc:
        raise ParseError(f"Syntax error in {file_path}:{exc.lineno}: {exc.msg}") from exc
```

- Also catch `ValueError` (null bytes) and `UnicodeDecodeError` -> `ParseError`.
- Never `compile()` or execute the source.

### 4.2 Implement module FQN computation (2 h)

```python
def compute_module_fqn(file_path: Path, package_root: Path, module_root: Path) -> str:
    ...
```

Algorithm (spec `06-...md` §1.2):
1. Determine `module_root`: for application code, the directory containing the top-level
   package; for site-packages, the site-packages directory itself.
2. Take `file_path` relative to `module_root`.
3. If the relative path namespaces under a package root, strip the outer filesystem segment
   that is not part of the package.
4. Replace `\\` and `/` with `.`; strip `.py`.
5. If the leaf is `__init__`, drop it (`pkg/__init__.py -> pkg`).
6. If a top-level `.py` sits directly in `module_root`, its FQN is its stem.

Examples to satisfy in tests:
- `src/myapp/utils/http.py`, root=`src`, package_root=`src/myapp` -> `myapp.utils.http`
- `site-packages/requests/__init__.py` -> `requests`
- `site-packages/requests/api.py` -> `requests.api`

### 4.3 Implement the `ModuleAST` wrapper (1.5 h)

Use the contract from spec §3.2:

```python
@dataclass
class ModuleAST:
    file_path: str
    module_fqn: str
    tree: ast.AST
    symbol_table: dict[str, str] = field(default_factory=dict)
    imports: dict[str, str] = field(default_factory=dict)
```

- `symbol_table`/`imports` are populated later by S2-T5/S2-T6; keep them empty here with
  documented ownership.
- Provide `iter_nodes()` helper delegating to `ast.walk` for convenience.

### 4.4 Implement the `ASTBuilder` orchestration (2 h)

```python
class ASTBuilder:
    def __init__(self, module_root: Path, package_root: Path | None = None) -> None: ...
    def build_file(self, path: Path) -> ModuleAST | None: ...
    def build_all(self, files: Iterable[SourceFile]) -> list[ModuleAST]: ...
```

- `build_file` reads text, parses, computes FQN, returns `ModuleAST`; on `OSError`/
  `UnicodeDecodeError`/`SyntaxError` log a WARNING with the path/line and return `None`
  (do not abort the scan).
- `build_all` skips `None` results and tracks a `skipped` count for reporting.
- Cache by `(path, mtime)` to avoid re-parsing during a single run.

### 4.5 Write tests (1.5 h)

Create `tests/unit/ast/test_builder.py`:

| Test | Assertion |
|------|-----------|
| `test_build_module_ast` | returns `ModuleAST` with valid `ast.AST` |
| `test_module_fqn_package_module` | `myapp.utils.http` |
| `test_module_fqn_init` | `__init__.py` -> package name |
| `test_module_fqn_top_level` | `main.py` -> `main` |
| `test_syntax_error_returns_none_and_warns` | `None` + `caplog` warning |
| `test_unsupported_encoding` | `ParseError`/warning, no crash |
| `test_parses_50_files` | repository fixture of 50 `.py` files all parse |
| `test_build_all_skips_invalid` | mixed valid/invalid list |

Generate a 50-file corpus fixture programmatically (or use installed libs) to satisfy the
roadmap criterion "parses 50 diverse Python files without syntax errors".

## Deliverables

- `pyreach/ast/builder.py`
- `pyreach/ast/__init__.py`
- `tests/unit/ast/test_builder.py`

## Acceptance Criteria

- Parses 50 diverse Python files without syntax errors; skips invalid files with warning.
  ✅ (roadmap S2-T4)
- FQN matches all documented examples.
- No file execution; only `ast.parse`.

## Verification

```bash
poetry run pytest tests/unit/ast/test_builder.py -q
poetry run pytest tests/unit/ast --cov=pyreach.ast --cov-report=term-missing
```

## Edge Cases & Pitfalls

- `ast.parse` needs `type_comments=True` to preserve `# type:` comments; decide and document.
- Python version grammar differences: parsing a 3.12-only file on 3.10 raises `SyntaxError`
  -> skip with warning, per spec.
- `__init__.py` at the root of a project with no package dir: FQN may be empty; guard.
- Namespace packages (no `__init__.py`) still deserve FQNs from their directories.

## Risks / Scope Cuts

- **R7 simplification fallback**: if package-root detection is unreliable, support only
  application-relative FQNs and treat site-packages roots as flat; document the accuracy
  trade-off.

## Definition of Done

- [ ] Builder + tests merged.
- [ ] 50-file parse test green.
- [ ] FQN examples documented and tested.
- [ ] Invalid files skipped with warnings, scan continues.
