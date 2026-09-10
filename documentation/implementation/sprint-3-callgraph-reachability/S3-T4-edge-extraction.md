# S3-T4 — Implement edge extraction: static calls, inheritance, imports

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 12 h |
| Dependencies | S3-T2, S3-T3, S2-T6 |
| Related docs | `06-ast-and-callgraph-engine.md` §2.3 (Edge Creation Pass), §2.4, §2.5, §2.6; `03-technical-specifications.md` §3.3 |

## Purpose

Create the directed `caller -> callee` edges that make reachability meaningful. This task
implements call-target resolution, method/`self` binding, inheritance edges, and the
conservative `DYNAMIC`/`<UNRESOLVED>` fallbacks mandated by risk R2.

## Preconditions

- Node pass merged.
- `ImportResolver` (S2-T6) available.
- Dynamic-pattern table from `06-...md` §2.6.

## Essential Sub-tasks

### 4.1 Implement the edge-extraction visitor (3 h)

In `pyreach/callgraph/engine.py`:

```python
class EdgeExtractor(ast.NodeVisitor):
    def __init__(self, module: ModuleAST, graph: nx.DiGraph, resolver: ImportResolver) -> None: ...
    def extract(self) -> None: ...
```

- Track the enclosing callable FQN while descending, so every `ast.Call` is attributed to the
  right caller (use a stack pushed on `visit_FunctionDef`/`visit_ClassDef`).
- For each `ast.Call`, resolve the target and add an edge from the current envelope to it.
- Skip calls inside non-callable scopes (class body executed at import) — attribute them to a
  synthetic `<module>` node or the class node; document the choice.

### 4.2 Implement call-target resolution (3 h)

- `ast.Name` (`foo()`): look up `symbol_table`, else treat as local/builtin.
- `ast.Attribute` chains (`obj.method()`, `pkg.func()`): use
  `ImportResolver.extract_attribute_chain` + `resolve_chain`.
- `obj.method()` where `obj` is a local variable bound to `Class()` (simple assignment
  tracking): resolve `obj` to its class if the assignment is a direct instantiation.
- Map resolved target to an existing node FQN; if the node is absent but the module exists,
  create a *placeholder* node (so library functions like `requests.api.get` are represented).
- Edge attributes: `edge_type="STATIC"`, `confidence=1.0`.

### 4.3 Implement method resolution (`self`/`cls`) and inheritance (3 h)

- `self.method()` -> replace the last component of the caller FQN with `method`
  (`mod.Class.caller` -> `mod.Class.method`).
- `cls.method()` -> same on the class node.
- If not found in the class, follow `INHERITANCE` edges to parent classes and search there.
- Build inheritance edges in a separate pass: for each class, for each resolved base, add
  `(SubClass -> BaseClass, edge_type="INHERITANCE", confidence=1.0)`.
- `super().method()` -> resolve to the parent's method.

### 4.4 Implement dynamic-pattern detection (2 h)

Flag a `DYNAMIC` edge for calls matching `06-...md` §2.6:

| Pattern | Detection |
|---------|-----------|
| `eval(...)`, `exec(...)` | `ast.Name` id in {`eval`,`exec`} |
| `getattr(obj, name)`, `setattr(...)` | `ast.Name` id in {`getattr`,`setattr`} |
| `__import__(...)` | `ast.Name` id `__import__` |
| `importlib.import_module(...)` | attribute chain ends with `import_module` |
| `apply(...)` | `ast.Name` id `apply` |
| unresolved `Name` not in symbol table | no target resolved |

- Add edge to a synthetic `"<DYNAMIC>"` node with `edge_type="DYNAMIC", confidence=0.5`.
- Unresolved names with no dynamic signature -> `"<UNRESOLVED>"` with confidence `0.3`.
- Also flag calls with `*args`/`**kwargs` where the function is unresolved.

### 4.5 Deterministic edge ordering and dedup (0.5 h)

- `DiGraph` collapses parallel edges; the last-written attributes win. To avoid
  nondeterminism, add edges in sorted order and prefer the highest-confidence type when an
  edge already exists (`STATIC` > `INHERITANCE` > `DYNAMIC`).
- Document the precedence rule.

### 4.6 Write tests (0.5 h)

Create `tests/unit/callgraph/test_edge_extraction.py`:

| Test | Assertion |
|------|-----------|
| `test_static_direct_call` | `main.main -> utils.helper` STATIC |
| `test_alias_call_edge` | `np.array` resolves to `numpy.array` |
| `test_self_method_resolution` | `self.other()` edge to class method |
| `test_inheritance_edge` | subclass -> base INHERITANCE |
| `test_super_call` | resolves to parent method |
| `test_dynamic_eval_edge` | `eval()` -> `<DYNAMIC>` with 0.5 |
| `test_unresolved_call_edge` | unknown name -> `<UNRESOLVED>` with 0.3 |
| `test_confidence_precedence` | STATIC wins over DYNAMIC on duplicate |
| `test_call_attributed_to_enclosing` | edge caller is enclosing function |
| `test_importlib_dynamic` | `importlib.import_module` flagged |

## Deliverables

- `pyreach/callgraph/engine.py` — edge pass + completeness of `CallGraphEngine.build`.
- `tests/unit/callgraph/test_edge_extraction.py`.

## Acceptance Criteria

- Correctly links `caller()` -> `callee()` for direct and method calls. ✅ (roadmap S3-T4)
- Inheritance and `super()` resolvable.
- Dynamic patterns always produce conservative `DYNAMIC`/`<UNRESOLVED>` edges, never missing.

## Verification

```bash
poetry run pytest tests/unit/callgraph/test_edge_extraction.py -q
poetry run pytest tests/unit/callgraph --cov=pyreach.callgraph --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Attribute chains through instance attributes are dynamic — must not silently become
  STATIC false positives; downgrade confidence.
- Recursion (`f -> f`) is valid and must be added.
- Calls in default arguments/decorators execute at definition time; attribute them to the
  module/class scope, not the function body.
- Conditional definitions mean two possible callees; add edges to both (conservative).

## Risks / Scope Cuts

- **R2 (dynamic false negatives)**: if dynamic detection lags, default all unresolved calls to
  `POTENTIALLY_REACHABLE` (S3-T6) rather than `NOT_REACHABLE`. Never remove the fallback.
- **R1**: dense graphs — rely on `DiGraph` edge collapsing (implemented in 4.5).

## Definition of Done

- [ ] Edge extractor + tests merged.
- [ ] All dynamic patterns from the spec covered.
- [ ] Conservative fallbacks present and tested.
- [ ] Coverage >=85% on `callgraph/`.
