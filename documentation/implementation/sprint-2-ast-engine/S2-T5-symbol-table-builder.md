# S2-T5 — Implement `SymbolTableBuilder`: map local names, imports, `from...import`

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 10 h |
| Dependencies | S2-T4 |
| Related docs | `06-ast-and-callgraph-engine.md` §1.3; `03-technical-specifications.md` §3.2; `08-testing-strategy.md` §4.2 |

## Purpose

Build the per-module lookup that lets the call-graph engine resolve a local identifier
(`np`, `OD`, `sibling`) to a fully qualified origin (`numpy`, `collections.OrderedDict`,
`current_pkg.sibling`). Without an accurate symbol table, alias resolution (S2-T6) and call
target resolution (S3-T4) cannot work.

## Preconditions

- S2-T4 `ModuleAST` available.
- S2-T1 notes on `ast.Import`/`ast.ImportFrom` semantics.
- A loader available to read the target module for star-import resolution.

## Essential Sub-tasks

### 5.1 Define the symbol table data model (0.5 h)

Add to `pyreach/ast/symbols.py`:

```python
@dataclass
class SymbolEntry:
    local_name: str
    fqn: str                 # resolved fully qualified name
    kind: Literal["module", "class", "function", "name", "star"]
    import_node: ast.AST | None = None
```

`ModuleAST.symbol_table: dict[str, str]` stores `local_name -> fqn` (contract in spec §3.2).
Keep `SymbolEntry` as an internal richer representation and expose the simple mapping.

### 5.2 Implement `visit_Import` handling (1.5 h)

For `ast.Import(names=[alias])`:

- `import os` -> `{"os": "os"}`.
- `import numpy as np` -> `{"np": "numpy"}`.
- `import a.b.c` -> `{"a": "a"}` (top-level binding only) **and** record
  `module_binding["a.b.c"] = ...` for attribute resolution; document the rule.
- `import a.b.c as abc` -> `{"abc": "a.b.c"}`.

### 5.3 Implement `visit_ImportFrom` handling (2 h)

For `ast.ImportFrom(module, names, level)`:

- `from collections import OrderedDict` -> `{"OrderedDict": "collections.OrderedDict"}`.
- `from collections import OrderedDict as OD` -> `{"OD": "collections.OrderedDict"}`.
- `from . import sibling` (`level=1`, `module=None`) -> `{"sibling": "<current_pkg>.sibling"}`.
- `from ..parent import mod` (`level=2`) -> `{"mod": "<parent_pkg>.parent.mod"}`.
- `from module import *` -> handled in 5.4.

Compute the absolute base module from `level` and `ModuleAST.module_fqn`:
drop `level-1` trailing package components, then append `module` if present.

### 5.4 Implement star-import resolution (2 h)

For `from module import *`:

1. Locate the target module's source file using the loader (`module` -> file path).
2. Parse it (reuse `ASTBuilder`).
3. If the target defines `__all__` as a list/tuple of string literals, import exactly those.
4. Otherwise, import every top-level `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, and
   assigned name (heuristic).
5. Insert entries with `kind="star"` and `fqn="<module>.<name>"`.
6. If the target cannot be found, record a `star` marker so the resolver can downgrade
   affected calls to `POTENTIALLY_REACHABLE` rather than `NOT_REACHABLE`.

Guard against circular star imports with a visited-module set.

### 5.5 Implement the `SymbolTableBuilder` visitor (2 h)

```python
class SymbolTableBuilder(ast.NodeVisitor):
    def __init__(self, module: ModuleAST, loader: Callable[[str], ModuleAST | None]) -> None: ...
    def build(self) -> dict[str, str]: ...
```

- Walk only module scope for imports, but also track assignments for simple aliasing
  (`Client = requests.Session` -> `Client` maps to `requests.Session`) where trivially
  resolvable.
- Detect name shadowing: a later import/assignment overrides an earlier binding (last wins).
- Do not descend into function/class bodies for import collection unless the import is at
  module scope; document this (function-local imports are handled during call resolution as
  best-effort).

### 5.6 Integrate with `ModuleAST` (0.5 h)

Populate `module.symbol_table` and `module.imports` after building. `imports` maps
`imported_name -> source_module` per spec §3.2.

### 5.7 Write tests (1.5 h)

Create `tests/unit/ast/test_symbols.py`:

| Test | Assertion |
|------|-----------|
| `test_import_plain` | `os -> os` |
| `test_import_alias` | `np -> numpy` |
| `test_import_dotted` | `a -> a` binding present |
| `test_from_import` | `OrderedDict -> collections.OrderedDict` |
| `test_from_import_alias` | `OD -> collections.OrderedDict` |
| `test_relative_import` | `sibling -> current_pkg.sibling` |
| `test_relative_parent_import` | `mod -> parent.mod` |
| `test_star_import_with_all` | only `__all__` names imported |
| `test_star_import_without_all` | top-level defs imported |
| `test_unresolvable_star_marks_star` | marker prevents false NOT_REACHABLE |
| `test_shadowing_last_wins` | later binding overrides |
| `test_circular_star_import_terminates` | no infinite recursion |

## Deliverables

- `pyreach/ast/symbols.py`
- `tests/unit/ast/test_symbols.py`
- Updated `ModuleAST` population path.

## Acceptance Criteria

- Correctly resolves `import numpy as np`, `from x import y as z`, `from . import sibling`.
  ✅ (roadmap S2-T5)
- Star-import resolution uses `__all__` when available.
- Unresolvable imports never cause a crash and are flagged for conservative classification.

## Verification

```bash
poetry run pytest tests/unit/ast/test_symbols.py -q
poetry run pytest tests/unit/ast --cov=pyreach.ast --cov-report=term-missing
```

## Edge Cases & Pitfalls

- `ast.ImportFrom.level` is 0 for absolute imports; `module` can be `None` for `from . import`.
- Re-exported names in `__init__.py` (e.g. `from .api import get`) are common; the visitor
  handles them naturally at module scope.
- `__all__` may be built dynamically (`__all__ = [...] + other`); if not a static list of
  strings, fall back to the top-level heuristic.
- Conditional imports (`try/except ImportError`) should keep the first successful binding but
  record both candidates if ambiguous; document behavior.

## Risks / Scope Cuts

- **Scope cut #2** (`10-risk-and-contingency-plan.md` §3): drop star-import resolution if
  Sprint 2 slips >3 days. Keep the `star` marker so calls remain `POTENTIALLY_REACHABLE`.

## Definition of Done

- [ ] Symbol builder + tests merged.
- [ ] `ModuleAST.symbol_table` populated by `ASTBuilder` pipeline.
- [ ] Star imports handled or explicitly downgraded.
- [ ] Coverage >=85% on `ast/`.
