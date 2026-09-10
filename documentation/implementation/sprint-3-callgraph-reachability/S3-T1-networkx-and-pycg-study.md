# S3-T1 — Study NetworkX DiGraph APIs and PyCG paper algorithms (Mitigation M3)

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 8 h |
| Dependencies | Reads S2 outputs; no code dependencies |
| Related docs | `06-ast-and-callgraph-engine.md` §2, §3; `10-risk-and-contingency-plan.md` §2 R1, §3 |

## Purpose

De-risk call-graph construction (Mitigation **M3**) by mastering `networkx.DiGraph` and the
PyCG paper's node/edge model before implementing S3-T3/T4. Output is verified knowledge and a
reference cheat-sheet, not shipped features.

## Preconditions

- `networkx>=3.0` installed.
- Access to `06-ast-and-callgraph-engine.md` and the PyCG paper (arXiv:2103.00587).
- Python REPL.

## Essential Sub-tasks

### 1.1 Learn DiGraph fundamentals (2 h)

- Create, add nodes/edges with attributes, query `successors`, `predecessors`,
  `get_edge_data`, `has_path`, `subgraph`.
- Understand node identity: `CGNode` is frozen/hashable, so it can be a node directly, but
  Sprint 3 prefers storing `fqn` strings as node keys with attributes (avoids duplicate
  objects and matches the SQLite cache). Decide and document.
- Benchmark add/get on a 10k-node graph to internalize cost.

### 1.2 Study traversal and shortest paths (2 h)

- `nx.bfs_tree`, `nx.dfs_tree`, `nx.single_source_shortest_path`,
  `nx.all_simple_paths` (and why it is exponential -> avoid for reachability).
- Implement an ad-hoc depth-limited BFS to confirm the algorithm in `06-...md` §3.2.
- Understand `tracemalloc` for measuring graph memory.

### 1.3 Study graph serialization (1 h)

- `nx.node_link_data` / `node_link_graph` for JSON persistence.
- How to load/save into SQLite via the `cg_nodes`/`cg_edges` tables (`05-...md`).
- Confirm `DiGraph` (not `MultiDiGraph`) collapses parallel edges — required by R1 mitigation.

### 1.4 Study PyCG node/edge model (2 h)

From the PyCG paper, map:

| PyCG concept | PyReach equivalent |
|--------------|---------------------|
| Namespaces / modules | `module_fqn` |
| Function/method definitions | `CGNode` FUNCTION/METHOD |
| Call edges | `CGEdge` `STATIC` |
| Dynamic calls | `CGEdge` `DYNAMIC` |
| Inheritance | `CGEdge` `INHERITANCE` |
| Import edges | `CGEdge` `IMPORT` |

Document where PyCG's points-to analysis is **out of scope** and how PyReach's conservative
heuristic compensates (R2).

### 1.5 Produce the study notes (1 h)

Create `documentation/study/callgraph-notes.md` with:
- Node-identity decision (string keys vs `CGNode` objects) and rationale.
- The verified depth-limited BFS snippet.
- Memory/serialization findings.
- PyCG mapping table and explicitly excluded features.
- A self-check: *"Can build, traverse, and serialize DiGraphs; understands PyCG node/edge
  types."*

## Deliverables

- `documentation/study/callgraph-notes.md`
- Optional scratch benchmark script under `scripts/study/`.

## Acceptance Criteria

- Can build, traverse, and serialize DiGraphs; understands PyCG node/edge types. ✅ (roadmap S3-T1)
- Node-identity decision recorded and adopted by S3-T2.
- Depth-limited BFS confirmed to terminate on cyclic graphs.

## Verification

- Demo to Julio: build a 3-node graph, serialize, reload, run depth-limited BFS.
- Show a 10k-node benchmark result.

## Edge Cases & Pitfalls

- `nx.Graph` vs `DiGraph`: using the undirected variant would break directionality of calls.
- `all_simple_paths` explodes on dense graphs — never use it for the full scan.
- Node attribute mutation on frozen dataclass nodes fails if `CGNode` is used as the key AND
  stored in attributes; pick one representation.

## Risks / Scope Cuts

- **R1 (combinatorial explosion)**: if benchmarks show memory pressure at 10k nodes, pre-decide
  the pruning/lazy-loading policy for S3-T3 (see `10-...md` §2 R1).

## Definition of Done

- [ ] Notes committed and reviewed.
- [ ] Node-identity decision frozen for S3-T2.
- [ ] BFS prototype verified on a cycle.
- [ ] Serialization round-trip demonstrated.
