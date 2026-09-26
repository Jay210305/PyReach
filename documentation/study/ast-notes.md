# AST Module Study Notes — Mitigation M1 (S2-T1)

> Internal reference document for Sprint 2 implementation tasks (S2-T4 through S2-T6).
> Not user-facing. Produced as part of Risk R7 mitigation.

---

## 1. Node Taxonomy

The following `ast` node types are relevant to PyReach's call graph construction:

| Node Type | Creates CG Node? | Creates CG Edge? | Key Fields | PyReach Usage |
|-----------|:-:|:-:|------------|---------------|
| `Module` | — | — | `body: list[stmt]` | Entry container; iterated for top-level definitions |
| `FunctionDef` | ✅ | — | `name`, `args`, `body`, `decorator_list`, `returns`, `lineno` | Graph nodes (FUNCTION) |
| `AsyncFunctionDef` | ✅ | — | Same as `FunctionDef` | Treated identically to `FunctionDef` |
| `ClassDef` | ✅ | — | `name`, `bases`, `body`, `decorator_list`, `lineno` | Graph nodes (CLASS); `bases` → INHERITANCE edges |
| `Lambda` | ✅ | — | `args`, `body`, `lineno` | Graph nodes (LAMBDA); anonymous, FQN = `module.enclosing.<lambda>` |
| `Call` | — | ✅ | `func`, `args`, `keywords`, `lineno` | Primary edge source: caller invokes callee |
| `Name` | — | — | `id`, `ctx` | Simple identifier in call (`foo()`) → resolve via symbol table |
| `Attribute` | — | — | `value`, `attr`, `ctx` | Dotted access in call (`obj.method()`) → resolve chain |
| `Import` | — | — | `names: list[alias]` (each has `name`, `asname`) | Populates symbol table: `import X as Y` → `Y → X` |
| `ImportFrom` | — | — | `module`, `names`, `level` | Populates symbol table; `level > 0` = relative import |
| `Assign` | — | — | `targets`, `value` | Simple binding tracking (`x = some_func`) |
| `AnnAssign` | — | — | `target`, `annotation`, `value` | Type-annotated assignment; annotation is NOT a call edge |
| `Return` | — | — | `value` | Detect returned callables (edge in advanced analysis) |
| `Decorator` | — | ✅ | (part of `decorator_list` on FunctionDef/ClassDef) | `@decorator` = implicit call at definition time |

### Key observations

- `AsyncFunctionDef` shares the exact same fields as `FunctionDef`; handle with a single
  visitor by checking `isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))`.
- `Lambda` has no `name`; assign synthetic FQN `<enclosing>.lambda_L{lineno}`.
- `decorator_list` entries are expressions; if they are `Call` nodes, the decorator itself
  is being called. Both patterns must generate edges.

---

## 2. Traversal Patterns

### 2.1 `ast.walk` vs `ast.NodeVisitor`

| Aspect | `ast.walk(tree)` | `ast.NodeVisitor` subclass |
|--------|-------------------|---------------------------|
| Order | Breadth-first (unspecified children order) | Depth-first (pre-order) |
| Parent context | ❌ Lost — only yields nodes flat | ✅ Maintained via the call stack |
| Use case | Quick flat scans (count all Calls) | Structured traversal (associate Call with enclosing FunctionDef) |

**PyReach choice:** Use `NodeVisitor` subclass for the main AST builder because we need
parent context (which function does a call belong to). Use `ast.walk` only for quick
utility lookups (e.g., "does this module contain any `import *`?").

### 2.2 Distinguishing call targets

```python
# Simple name call: ast.Name
foo()           # node.func = Name(id='foo')

# Attribute call: ast.Attribute
obj.method()    # node.func = Attribute(value=Name(id='obj'), attr='method')

# Chained attribute: nested Attribute
a.b.c()         # node.func = Attribute(
                #   value=Attribute(value=Name(id='a'), attr='b'),
                #   attr='c'
                # )

# Direct class instantiation via Call:
MyClass()       # node.func = Name(id='MyClass')
```

To resolve the fully-qualified callee:
1. If `func` is `Name`: look up `name.id` in the symbol table.
2. If `func` is `Attribute`: recursively resolve the `value` chain, then append `.attr`.

### 2.3 Detecting entry points

```python
# Pattern: if __name__ == "__main__":
for node in ast.walk(tree):
    if isinstance(node, ast.If):
        # Check: Compare(left=Name(id='__name__'), ops=[Eq], comparators=[Constant(value='__main__')])
        test = node.test
        if (isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"):
            # node.body contains the entry point statements
            ...
```

---

## 3. Import Resolution

### 3.1 `ast.Import` vs `ast.ImportFrom`

```python
# ast.Import
import os                    # names=[alias(name='os', asname=None)]
import numpy as np           # names=[alias(name='numpy', asname='np')]

# ast.ImportFrom
from collections import OrderedDict          # module='collections', names=[alias(name='OrderedDict')], level=0
from collections import OrderedDict as OD    # module='collections', names=[alias(name='OrderedDict', asname='OD')], level=0
from . import sibling                        # module=None, names=[alias(name='sibling')], level=1
from ..parent import mod                     # module='parent', names=[alias(name='mod')], level=2
from module import *                         # module='module', names=[alias(name='*')], level=0
```

### 3.2 Relative import level semantics

- `level=0` → absolute import
- `level=1` → current package (`.`)
- `level=2` → parent package (`..`)
- `level=N` → N levels up

To resolve: take the current module's FQN, strip N trailing components, then append
`node.module` (if present) and the imported name.

### 3.3 Star import handling

When encountering `from module import *`:
1. Locate the target module's source file via `PackageResolver`.
2. Parse its AST.
3. If `__all__` is defined as a list of string constants, import those names.
4. Otherwise, import all top-level `FunctionDef`, `ClassDef`, and `Assign` target names
   that don't start with `_`.
5. If resolution fails → log a WARNING and mark all references from that module as
   `POTENTIALLY_REACHABLE` (conservative).

---

## 4. FQN Algorithm

Given a file's absolute path and a known root directory:

```
Algorithm compute_module_fqn(file_path, root):
    rel = file_path.relative_to(root)
    parts = rel.with_suffix("").parts       # strip .py, split by separator
    if parts[-1] == "__init__":
        parts = parts[:-1]                  # package __init__ → package FQN
    return ".".join(parts)
```

### Verified examples

| File Path (relative to root) | FQN |
|------------------------------|-----|
| `myapp/utils/http.py` | `myapp.utils.http` |
| `myapp/__init__.py` | `myapp` |
| `myapp/cli.py` | `myapp.cli` |
| `requests/api.py` (in site-packages) | `requests.api` |
| `requests/__init__.py` | `requests` |
| `requests/packages/urllib3/response.py` | `requests.packages.urllib3.response` |
| `flask/app.py` | `flask.app` |
| `flask/__init__.py` | `flask` |
| `single_module.py` | `single_module` |
| `src/myapp/core/engine.py` | `src.myapp.core.engine` |

> **Gotcha (Windows):** `Path.parts` uses `\\` on Windows. Always convert with
> `"/".join(...)` or use `PurePosixPath` for FQN computation. The algorithm above
> uses `".".join(parts)` which is separator-agnostic since `parts` is a tuple of
> individual directory/file names.

---

## 5. Syntax Errors and Recovery

- `ast.parse()` raises `SyntaxError` with attributes: `msg`, `lineno`, `offset`, `filename`, `text`.
- **PyReach policy:** never abort the scan on a single file's syntax error. Catch
  `SyntaxError`, log a WARNING with path and line, skip the file, and continue.
- Files with encoding errors (BOM issues, binary files) also raise `SyntaxError` or
  `UnicodeDecodeError`; handle both.
- Python 3.12+ f-string grammar changes may cause `SyntaxError` when parsing with an older
  Python; this is acceptable since we target `>=3.10` compatible source.

---

## 6. Gotchas for Implementation Tasks

### For S2-T4 (ASTBuilder)

1. Always pass `filename=` to `ast.parse()` so error messages include the path.
2. Use `type_comments=False` (default) — type comments are Python 2 legacy.
3. `ast.dump(node, include_attributes=True)` is essential for debugging; include line numbers.
4. `node.lineno` may not exist on all node types (e.g., `arguments`, `comprehension`);
   always use `getattr(node, 'lineno', None)`.

### For S2-T5 (SymbolTableBuilder)

5. `from X import *` — must be resolved lazily; the target module may not be parsed yet.
   Queue these and resolve in a second pass.
6. Conditional imports (`try: import X / except ImportError: X = None`) — treat as
   binding `X` to the attempted module. Both branches may define the same name.
7. Aliased imports create only one symbol table entry (the alias, not the original name).
8. `import a.b.c` creates a binding for `a`, not for `a.b.c`; but `from a.b import c`
   creates a binding for `c` mapped to `a.b.c`.

### For S2-T6 (ImportResolver)

9. Relative imports require knowing the current module's package; pass this as context.
10. Circular imports are possible; use a visited set to avoid infinite loops.
11. Namespace packages (no `__init__.py`) are common in modern Python; check for directory
    existence even without `__init__.py`.
12. `importlib.metadata` can provide installed package → path mapping but is slow for bulk
    resolution; cache results.

### General

13. Nested functions get FQN `module.outer.inner`; nested classes get `module.Outer.Inner`.
14. Methods inside nested classes: `module.Outer.Inner.method`.
15. `global`/`nonlocal` do not affect import resolution (they affect name binding scope).
16. Type hints (`x: SomeType`) should NOT create call edges; only `Call` nodes do.
17. Decorators ARE calls: `@deco` is equivalent to `func = deco(func)`.

---

## 7. Self-Assessment Checklist

- [x] Can explain the difference between `ast.walk` and `NodeVisitor` with tradeoffs.
- [x] Can extract all function/class names from a Python file using `NodeVisitor`.
- [x] Can identify `Call` nodes and distinguish `Name` from `Attribute` call targets.
- [x] Can handle `AsyncFunctionDef` identically to `FunctionDef`.
- [x] Can extract decorator expressions and their arguments.
- [x] Can parse `if __name__ == "__main__":` blocks.
- [x] Can explain `Import` vs `ImportFrom` fields including `level` for relative imports.
- [x] Can compute FQN from file path for regular modules and `__init__.py` files.
- [x] Can handle `SyntaxError` gracefully without aborting the scan.
- [x] Can identify edge cases: nested functions, conditional imports, star imports.
