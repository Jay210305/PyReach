# S3-T2 — Design `CGNode` and `CGEdge` dataclasses with type annotations

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 4 h |
| Dependencies | S3-T1 (node-identity decision) |
| Related docs | `03-technical-specifications.md` §3.3; `06-ast-and-callgraph-engine.md` §2.1, §2.2; `05-data-model-and-storage.md` (§cg_nodes/cg_edges) |

## Purpose

Freeze the immutable graph data model used by the builder (S3-T3/T4), the analyzer (S3-T5),
and the SQLite cache. Because it is consumed everywhere, it must be decided once and reviewed.

## Preconditions

- S3-T1 study complete (node-identity decision made).
- `packaging`/stdlib only; no new deps.

## Essential Sub-tasks

### 2.1 Implement `CGNode` per spec §3.3 (1 h)

In `pyreach/callgraph/nodes.py`:

```python
NodeType = Literal["FUNCTION", "METHOD", "CLASS", "LAMBDA"]

@dataclass(frozen=True, order=True)
class CGNode:
    fqn: str
    file_path: str | None = None
    line_number: int | None = None
    node_type: NodeType = "FUNCTION"
```

- `frozen=True` and `order=True` so nodes are hashable and sortable (deterministic output).
- Validate `node_type` in `__post_init__`; raise `AnalysisError` (add to exceptions) on invalid.
- Provide `is_lambda` / `is_callable` helpers and `__str__` returning `fqn`.

### 2.2 Implement `CGEdge` per spec §3.3 (1 h)

In `pyreach/callgraph/edges.py`:

```python
EdgeType = Literal["STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"]

@dataclass(frozen=True)
class CGEdge:
    caller: CGNode
    callee: CGNode
    edge_type: EdgeType
    confidence: float = 1.0
```

- Validate `confidence` in `[0.0, 1.0]`; raise `AnalysisError` otherwise.
- Validate `edge_type` against the allowed set.
- Provide `is_dynamic` property used by the classifier.

### 2.3 Define node/edge key conventions (0.5 h)

- Graph stores node keys as `fqn` strings; `CGNode` attributes are attached to the node
  (`G.nodes[fqn] = {"node": CGNode, "node_type": ...}`) to keep traversal cheap.
- Edges store `{"edge_type": ..., "confidence": ...}`.
- Document that lambda FQNs use `"<lambda>:<file>:<line>"` (`06-...md` §2.1).
- Document synthetic sentinel nodes: `"<DYNAMIC>"` and `"<UNRESOLVED>"`.

### 2.4 Add converters for SQLite cache (0.5 h)

- `CGNode.to_row()` / `from_row()` mapping to `cg_nodes` columns.
- `CGEdge` serialization for `cg_edges` (caller_id/callee_id resolved via node ids).
- Keep converters here so S3-T5/S4 can persist/restore without duplicating logic.

### 2.5 Write tests (1 h)

Create `tests/unit/callgraph/test_nodes.py` and `test_edges.py`:

| Test | Assertion |
|------|-----------|
| `test_cgnode_frozen` | mutation raises `FrozenInstanceError` |
| `test_cgnode_hashable` | usable in a set/dict key |
| `test_cgnode_validates_type` | bad `node_type` -> `AnalysisError` |
| `test_cgnode_sort_order` | deterministic sorting by fqn |
| `test_cgedge_validates_confidence` | `<0` or `>1` -> `AnalysisError` |
| `test_cgedge_validates_type` | bad edge type -> `AnalysisError` |
| `test_cgedge_is_dynamic` | true only for `DYNAMIC` |
| `test_node_row_roundtrip` | `from_row(to_row(n)) == n` |
| `test_edge_row_roundtrip` | caller/callee preserved |

## Deliverables

- `pyreach/callgraph/nodes.py`
- `pyreach/callgraph/edges.py`
- `pyreach/callgraph/__init__.py`
- `tests/unit/callgraph/test_nodes.py`, `tests/unit/callgraph/test_edges.py`
- `AnalysisError` added to `pyreach/exceptions.py`.

## Acceptance Criteria

- Reviewed by Julio; documented; immutable/frozen. ✅ (roadmap S3-T2)
- Field names/types match spec §3.3 exactly.
- Row converters round-trip cleanly.

## Verification

```bash
uv run pytest tests/unit/callgraph/test_nodes.py tests/unit/callgraph/test_edges.py -q
uv run mypy pyreach/callgraph/nodes.py pyreach/callgraph/edges.py
```

## Edge Cases & Pitfalls

- `Literal` types are not enforced at runtime; `__post_init__` must validate.
- Two `CGNode`s with the same FQN but different line numbers must not both become graph nodes;
  dedupe by `fqn` at build time (document whose responsibility that is: S3-T3).
- `confidence` default must be `1.0` (certain) per spec.

## Risks / Scope Cuts

- None. This is a small, foundational task; do not cut it.

## Definition of Done

- [ ] Dataclasses + converters merged.
- [ ] Julio's review recorded.
- [ ] `AnalysisError` available.
- [ ] Tests green and types clean.
