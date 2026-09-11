# S2-T6 — Implement `ImportResolver`: cross-module alias to fully qualified names

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 8 h |
| Dependencies | S2-T4, S2-T5 |
| Related docs | `06-ast-and-callgraph-engine.md` §1.3, §2.4; `03-technical-specifications.md` §3.2 |

## Purpose

Convert a local name (or attribute chain) into a fully qualified name across modules and
packages: given `import requests`, resolve `requests.get` to `requests.api.get`. This is the
bridge between the per-module symbol table and the call-graph edge resolver.

## Preconditions

- `SymbolTableBuilder` merged and populating `ModuleAST.symbol_table`.
- `PackageResolver` (S2-T3) available to locate library module files when needed.
- An index of all `ModuleAST` objects keyed by FQN.

## Essential Sub-tasks

### 6.1 Define the module index (1 h)

In `pyreach/ast/resolver.py`:

```python
class ModuleIndex:
    def __init__(self, modules: Iterable[ModuleAST]) -> None: ...
    def get(self, fqn: str) -> ModuleAST | None: ...
    def find_symbol(self, fqn: str) -> str | None: ...
```

- Key by `module_fqn`.
- `find_symbol("requests.get")` should, when the exact submodule isn't available, check
  whether `get` is re-exported from `requests/__init__.py` (re-export resolution).
- Handle package vs module: `requests` may be a package whose `__init__` re-exports `get`
  from `requests.api`.

### 6.2 Implement single-name resolution (1.5 h)

`resolve_name(local: str, module: ModuleAST) -> str | None`:

- Look up `module.symbol_table[local]`.
- If found, return the FQN.
- If it is a top-level binding (e.g. a function defined in this module), return
  `f"{module.module_fqn}.{local}"`.
- If not found locally, check builtins (`len`, `print`) -> return the name itself so callers
  can classify calls to builtins without creating spurious package edges.

### 6.3 Implement attribute-chain resolution (2.5 h)

`resolve_attribute_chain(chain: list[str], module: ModuleAST) -> str | None`:

- If `chain[0]` is in the symbol table, replace it with its FQN and append the rest:
  `["requests","get"]` with `symbol_table["requests"]="requests"` -> `requests.get`.
- If `chain[0] == "self"` -> delegate to method resolution (`<Class>.<attr>`); this is used by
  S3-T4 and must be exposed as a helper.
- If `chain[0] == "cls"` -> class-level method resolution.
- If the base is an imported alias, expand: `["np","array"]` ->
  `numpy.array`.
- If none of the above, return the dotted chain unchanged, but mark it *unresolved*.

### 6.4 Implement cross-module validation / disambiguation (2 h)

- After producing a candidate FQN, verify it against `ModuleIndex`:
  - If the module prefix exists and the attribute is defined/re-exported, confidence = HIGH.
  - If the module prefix exists but the attribute is unknown, confidence = MEDIUM.
  - If the module prefix doesn't exist, confidence = LOW (unresolved).
- Return both the FQN and a confidence value (0.0-1.0). The call-graph engine maps
  confidence < 1.0 to `edge_type=DYNAMIC` per `06-...md` §2.2.
- Re-export resolution: `requests/__init__.py` with `from .api import get` means
  `requests.get` should be allowed to resolve to `requests.api.get` (choose the original
  definition when available, else the re-export path).

### 6.5 Expose the resolver API (0.5 h)

```python
class ImportResolver:
    def __init__(self, index: ModuleIndex) -> None: ...
    def resolve_name(self, name: str, module: ModuleAST) -> str | None: ...
    def resolve_chain(self, chain: list[str], module: ModuleAST) -> ResolvedTarget: ...
    @staticmethod
    def extract_attribute_chain(node: ast.AST) -> list[str]: ...
```

`ResolvedTarget` = dataclass `(fqn: str, confidence: float, resolved: bool)`.

### 6.6 Write tests (0.5 h)

Create `tests/unit/ast/test_resolver.py`:

| Test | Setup | Expected |
|------|-------|----------|
| `test_resolve_imported_call` | `import requests`, `requests.get` | `requests.api.get` (via re-export) or `requests.get` |
| `test_resolve_alias_call` | `import numpy as np`, `np.array` | `numpy.array` |
| `test_resolve_from_import` | `from x import y`, `y()` | `x.y` |
| `test_resolve_local_function` | `def f()`, `f()` | `<module>.f` |
| `test_resolve_builtin` | `len()` | `len` with resolved flag false |
| `test_unresolved_chain` | `unknown.foo()` | confidence LOW |
| `test_self_method` | class method + `self.other()` | `<Class>.other` |
| `test_extract_attribute_chain` | `a.b.c()` | `["a","b","c"]` |
| `test_re_export_resolution` | package `__init__` re-export | maps to origin |

## Deliverables

- `pyreach/ast/resolver.py`
- `tests/unit/ast/test_resolver.py`

## Acceptance Criteria

- Given `import requests`, resolves `requests.get` to `requests.api.get`. ✅ (roadmap S2-T6)
- Absolute, relative, and star imports all resolvable (star uses S2-T5 output).
- Unresolved names carry low confidence and never throw.

## Verification

```bash
uv run pytest tests/unit/ast/test_resolver.py -q
uv run pytest tests/unit/ast --cov=pyreach.ast --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Same symbol may be reachable via multiple paths; pick the most specific and record
  alternatives for debugging.
- Re-exports can create cycles (`__init__` imports from submodule which imports `__init__`);
  use the `ModuleIndex` without triggering re-parsing loops.
- Attribute chains through instances (`self.db.connection.cursor`) are inherently dynamic;
  return low confidence rather than guessing.
- Dotted `import a.b` binds only `a` locally; `a.b` must be resolved by prefix match against
  the module binding recorded in S2-T5.

## Risks / Scope Cuts

- **R7 / scope cut #2**: if cross-module resolution slips, keep single-module resolution
  (S2-T5) and downgrade cross-package calls to `POTENTIALLY_REACHABLE`. Document the fallback.

## Definition of Done

- [ ] Resolver + tests merged.
- [ ] `requests.get` example passes.
- [ ] Confidence model documented and consumed by S3-T4.
- [ ] Coverage >=85% on `ast/`.
