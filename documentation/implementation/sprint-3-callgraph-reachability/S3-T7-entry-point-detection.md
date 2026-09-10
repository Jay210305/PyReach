# S3-T7 — Implement entry point auto-detection (`__main__`, CLI-configured)

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 4 h |
| Dependencies | S2-T4, S3-T3 |
| Related docs | `06-ast-and-callgraph-engine.md` §3.1; `03-technical-specifications.md` §4, §5; `07-sarif-and-cli-design.md` §2.2 |

## Purpose

Entry points are the roots of reachability. If none are found, every symbol becomes
`NOT_REACHABLE` (a catastrophic false-negative source). This task finds roots automatically
and honors explicit `-e` overrides.

## Preconditions

- `ModuleAST` pipeline available.
- Node pass (S3-T3) produces FQNs.
- CLI/config not yet built — expose a clean callable for Sprint 4.

## Essential Sub-tasks

### 7.1 Implement auto-detection rules (2 h)

In `pyreach/reachability/entrypoints.py`:

```python
class EntryPointDetector:
    def __init__(self, modules: Iterable[ModuleAST]) -> None: ...
    def detect(self) -> list[str]: ...
```

Detection rules (union, deterministically sorted):

1. Top-level function named `main` in any module -> `<module_fqn>.main`.
2. Any `if __name__ == "__main__":` block. Because the block is module-level code, record the
   **module** as an entry root (a synthetic node `<module_fqn>.__main__` created by the
   engine) and also any functions called directly inside the block.
3. Framework decorator heuristics:
   - FastAPI/Starlette: decorators ending in `.get`/`.post`/`.put`/`.delete`/`.patch` whose
     object is an `app`/`router`/`api` binding.
   - Flask: decorators ending in `.route` (any binding).
   - Django: **not** auto-detected (too diverse) — rely on `-e`.
4. Module-level `asyncio.run(...)` / `uvicorn.run(app, ...)` calls -> treat the module as an
   entry root and the referenced callable as an entry.
5. `console_scripts` from `pyproject.toml`/`setup.py` if present (best-effort; document).

### 7.2 Implement CLI/config override merging (1 h)

```python
def resolve_entry_points(
    detected: list[str],
    cli_entry_points: list[str],
    config_entry_points: list[str],
) -> list[str]: ...
```

- Union, de-duplicated.
- Accept both `pkg.mod:func` and `pkg.mod.func` forms; normalize `:` to `.`.
- If an override references an FQN not present in the graph, log a WARNING but keep it (the
  graph may create a placeholder node in S4 once library ASTs load).
- Precedence: CLI > config > auto-detect, but the final list is the union so nothing is lost.

### 7.3 Integrate with the analyzer (0.5 h)

- `analyze_reachability` receives this list; if empty, the caller (CLI) must raise a
  `ConfigError` with the message from `07-...md` §3 ("No entry points detected. Use -e ...").
- Provide `detect_or_fail(modules, overrides) -> list[str]` convenience that raises on empty
  unless `allow_empty=True` (used in tests).

### 7.4 Write tests (0.5 h)

Create `tests/unit/reachability/test_entrypoints.py`:

| Test | Fixture | Expected |
|------|---------|----------|
| `test_detect_main_function` | module with `def main()` | `<mod>.main` |
| `test_detect_dunder_main_block` | `if __name__ == "__main__"` | module entry present |
| `test_detect_fastapi_decorator` | `@app.get` | handler FQN detected |
| `test_detect_flask_route` | `@app.route` | handler FQN detected |
| `test_no_django_autodetect` | `@admin.register` | not detected |
| `test_cli_override_union` | detected + `-e` | union returned |
| `test_colon_normalized` | `pkg.mod:func` | `pkg.mod.func` |
| `test_unknown_override_kept_with_warning` | bad FQN | present + warning |
| `test_empty_raises` | none detected, no overrides | `ConfigError` |
| `test_asyncio_run_detected` | `asyncio.run(main())` | module/main detected |

## Deliverables

- `pyreach/reachability/entrypoints.py`
- `tests/unit/reachability/test_entrypoints.py`

## Acceptance Criteria

- Detects `if __name__ == "__main__"` and respects `-e` overrides. ✅ (roadmap S3-T7)
- FastAPI/Flask decorators auto-detected; Django explicitly not.
- Empty entry point set raises a clear `ConfigError` (not silent `NOT_REACHABLE` storm).

## Verification

```bash
poetry run pytest tests/unit/reachability/test_entrypoints.py -q
poetry run pytest tests/unit/reachability --cov=pyreach.reachability --cov-report=term-missing
```

## Edge Cases & Pitfalls

- `if __name__ == "__main__"` may use single quotes or `__name__ == '__main__'`; normalize by
  `ast.literal_eval` on the right-hand side.
- Decorator objects may be imported aliases (`from fastapi import FastAPI; app = FastAPI()`);
  resolve via the symbol table before comparing.
- Multiple `main` functions across modules: include all (union).
- A detected entry may be a class (for `uvicorn.run(app)`) — record the class node.

## Risks / Scope Cuts

- **R2**: if framework heuristics mis-detect, entry points merely grow (safe: more reachable).
  If they under-detect, symbols become false negatives. Prefer over-detection.

## Definition of Done

- [ ] Detector + tests merged.
- [ ] CLI/config override merge exposed for Sprint 4.
- [ ] Empty-entry `ConfigError` path tested.
- [ ] Coverage >=85% on `reachability/`.
