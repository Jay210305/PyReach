# S3-T3 — Implement node extraction: functions, methods, lambdas, classes

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 10 h |
| Dependencies | S2-T4, S2-T5, S3-T2 |
| Related docs | `06-ast-and-callgraph-engine.md` §2.1, §2.3 (Node Creation Pass); `03-technical-specifications.md` §3.3 |

## Purpose

Create one graph node for every callable (and class) discovered across all `ModuleAST`s, with a
unique, deterministic FQN. Nodes are the vertices the reachability analyzer traverses, so
completeness here directly affects false negatives.

## Preconditions

- `ModuleAST`s available from the S2 pipeline.
- `CGNode`/`CGEdge` frozen (S3-T2).
- `networkx>=3.0`.
- S3-T1 node-identity decision applied.

## Essential Sub-tasks

### 3.1 Implement the node-extraction visitor (2.5 h)

In `pyreach/callgraph/engine.py`:

```python
class NodeExtractor(ast.NodeVisitor):
    def __init__(self, module: ModuleAST, graph: nx.DiGraph) -> None: ...
    def extract(self) -> None: ...
```

- Module-level `FunctionDef`/`AsyncFunctionDef` -> `CGNode(fqn=f"{module}.{name}",
  node_type="FUNCTION")`.
- `ClassDef` -> `CGNode(fqn=f"{module}.{Class}", node_type="CLASS")`.
- Methods (functions directly inside a `ClassDef`) ->
  `CGNode(fqn=f"{module}.{Class}.{method}", node_type="METHOD")`.
- `Lambda` -> `CGNode(fqn=f"<lambda>:{rel_path}:{lineno}", node_type="LAMBDA")`.
- Nested functions -> qualify as `f"{enclosing_fqn}.<locals>.{name}"` and document the
  convention.

### 3.2 Compute canonical FQNs (2 h)

- Reuse `compute_fqn` helpers; never duplicate logic from S2-T4.
- Methods: parent class FQN + `.` + method name.
- Handle `@staticmethod`/`@classmethod`/`@property`: still `METHOD` nodes; record a
  `modifier` attribute (`"static"`, `"class"`, `"property"`) for edge resolution later.
- Deduplicate by `fqn`: if two definitions share an FQN (e.g. conditional defs), keep the
  first and log a DEBUG warning.
- Attach `file_path` (relative for SARIF) and `line_number`.

### 3.3 Attach node attributes and edge-creation handoff (1.5 h)

- `G.add_node(fqn, node=CGNode(...), node_type=..., file_path=..., line_number=...)`.
- Add scoping metadata consumed by S3-T4:
  - `class_fqn` for methods (the owning class).
  - `parent_fqn` for nested/local functions.
  - `is_async` boolean.
- Do **not** create edges here (single responsibility; S3-T4 owns edges).

### 3.4 Handle inheritance node metadata (1.5 h)

- For each `ClassDef`, record `bases` (resolved via the symbol table where possible) as node
  metadata; S3-T4 turns these into `INHERITANCE` edges.
- Record decorators on classes and functions (needed for entry-point detection in S3-T7).

### 3.5 Implement the public engine entry point (1 h)

```python
class CallGraphEngine:
    def __init__(self, index: ModuleIndex) -> None: ...
    def build(self, modules: Iterable[ModuleAST]) -> nx.DiGraph: ...
```

- `build` runs the node pass for all modules, then (in S3-T4) the edge pass.
- Return the `DiGraph`; expose `stats` (node counts by type).

### 3.6 Write tests (1.5 h)

Create `tests/unit/callgraph/test_node_extraction.py`:

| Test | Assertion |
|------|-----------|
| `test_function_node` | module function present with FUNCTION type |
| `test_async_function_node` | `AsyncFunctionDef` present |
| `test_method_node` | class method FQN `mod.Class.method` |
| `test_class_node` | class node present |
| `test_lambda_node` | lambda FQN includes file+line |
| `test_nested_function_locals_fqn` | `<locals>` convention |
| `test_dedup_same_fqn` | one node, no crash |
| `test_static_method_modifier` | modifier recorded |
| `test_line_and_file_metadata` | metadata matches source |
| `test_extracts_95_percent` | >=95% callables across corpus (S2-T7 samples) |

## Deliverables

- `pyreach/callgraph/engine.py` — `NodeExtractor`, `CallGraphEngine` (node pass).
- `tests/unit/callgraph/test_node_extraction.py`.

## Acceptance Criteria

- Extracts >=95% of callable nodes in standard Python code. ✅ (roadmap S3-T3)
- Deterministic, deduplicated FQNs.
- No edges created in this task.

## Verification

```bash
poetry run pytest tests/unit/callgraph/test_node_extraction.py -q
poetry run pytest tests/unit/callgraph --cov=pyreach.callgraph --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Multiple assignment of the same function name; keep first, warn.
- Comprehensions and generator expressions are not function nodes (do not add).
- Overloaded methods (same name) collapse to one node — expected in static analysis.
- Decorators can wrap a function so its runtime identity differs; still model the syntactic
  definition.

## Risks / Scope Cuts

- **R1**: if node counts explode, prune leaf functions that are neither vulnerable symbols nor
  reachable from an entry (defer pruning to S3-T5 analysis; document).

## Definition of Done

- [ ] Node extractor + tests merged.
- [ ] >=95% extraction demonstrated on the corpus.
- [ ] FQN conventions documented.
- [ ] Node metadata ready for S3-T4.
