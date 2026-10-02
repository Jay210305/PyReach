# Call Graph Study Notes — Mitigation M3 (S3-T1)

> Internal reference document for Sprint 3 implementation tasks (S3-T2 through S3-T8).
> Not user-facing. Produced as part of Risk R1/M3 mitigation.

---

## 1. Node Identity Decision

**Decision**: Use `fqn` strings as NetworkX node keys; store `CGNode` attributes in `G.nodes[fqn]`.

**Rationale**:

1. **SQLite cache alignment**: `cg_nodes` table stores `fqn TEXT` as the natural key. Storing strings as node keys means the graph and the cache use the same identifier without translation.
2. **Avoids duplicate objects**: Two `CGNode` instances with the same FQN but different `line_number` (e.g., conditional definitions) are distinct objects but represent the same graph vertex. String keys deduplicate naturally.
3. **Cheaper traversal**: String comparison is faster than dataclass comparison during BFS expansion.
4. **Frozen dataclass as key works but is risky**: `CGNode(frozen=True, order=True)` is hashable and can be a node key directly (verified: `hash(n1) == hash(n1)`, `n1 in {n1, n2}`). However, if you store the same `CGNode` object in both the key and the attributes, you get redundancy and potential inconsistency. Pick one representation.

**Convention**:

- Lambda FQNs: `"<lambda>:{rel_path}:{lineno}"` (e.g., `"<lambda>:app/utils.py:42"`)
- Synthetic sentinel nodes: `"<DYNAMIC>"`, `"<UNRESOLVED>"`
- Node attributes stored as: `G.nodes[fqn] = {"node": CGNode(...), "node_type": "...", "file_path": "...", "line_number": ...}`
- Edge attributes stored as: `G.edges[u, v] = {"edge_type": "...", "confidence": ...}`

**Pitfall avoided**: `nx.Graph` (undirected) would break call directionality. Always use `nx.DiGraph`.

---

## 2. Verified Depth-Limited BFS

Iterative BFS with `collections.deque`, never recursion (avoids Python recursion limit).

```python
from collections import deque

def depth_limited_bfs(graph, start, target, max_depth):
    """
    Returns (found: bool, path: list[str] | None, encountered_dynamic: bool).
    Terminates on cyclic graphs; bounded by max_depth.
    """
    queue = deque([(start, [start], 0)])
    visited = set()
    encountered_dynamic = False

    while queue:
        current, path, depth = queue.popleft()

        if depth > max_depth:
            continue
        if current in visited:
            continue
        visited.add(current)

        if current == target:
            return True, path, encountered_dynamic

        for successor in graph.successors(current):
            edge_data = graph.get_edge_data(current, successor)
            edge_type = edge_data.get("edge_type", "STATIC") if edge_data else "STATIC"

            if edge_type == "DYNAMIC":
                encountered_dynamic = True

            queue.append((successor, path + [successor], depth + 1))

    return False, None, encountered_dynamic
```

**Verification results**:

| Test | Result |
|------|--------|
| Simple path (entry → A → B → target, depth 3) | Found, path recorded ✅ |
| Depth limit exceeded (chain length 7, k=5) | Not found ✅ |
| Cyclic graph (A→B→C→A, target reachable) | Found, terminates ✅ |
| Self-loop (f→f, f→target) | Found, terminates ✅ |
| 100-node graph, 100 runs | ~0.00ms avg (well under 100ms budget) ✅ |

**Key insight**: The `visited` set prevents infinite expansion on cycles. The `depth > max_depth` check bounds the search. Both are necessary.

**Nondeterminism note**: When multiple paths exist, the BFS finds the shortest one first (BFS property). For deterministic output, sort paths before returning.

**Path collection bound**: Limit to at most N (e.g., 5) shortest paths to keep SARIF output small. Use `nx.all_simple_paths` only on very small subgraphs — it is exponential on dense graphs and must never be used for the full scan.

---

## 3. Memory and Serialization Findings

### 3.1 10k-node benchmark

| Metric | Value |
|--------|-------|
| Build time (10k nodes + 9,999 edges) | ~297ms |
| Peak memory | ~9.84 MB |
| `has_path(node_00000, node_09999)` | True |

Memory is well within bounds for typical microservices. The `tracemalloc` monitoring in tests is sufficient for R1 tracking.

### 3.2 JSON serialization (node_link_data)

- `nx.node_link_data(G)` produces `{"directed": true, "multigraph": false, "graph": {}, "nodes": [...], "edges": [...]}`
- Node attributes preserved in `nodes[].node_type`, `file_path`, `line_number`
- Edge attributes preserved in `edges[].edge_type`, `confidence`
- Round-trip: `nx.node_link_graph(data)` reconstructs identical graph ✅
- JSON size for 10k-node chain: ~several KB (compact)

**Key**: NetworkX 3.x uses `"edges"` key (not `"links"`) in node_link format. Verify your NetworkX version if round-trip fails.

### 3.3 SQLite integration

Tables from `pyreach/db/schema.sql`:

```sql
CREATE TABLE cg_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fqn TEXT NOT NULL UNIQUE,
    node_type TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER
);

CREATE TABLE cg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id INTEGER NOT NULL,
    callee_id INTEGER NOT NULL,
    edge_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    FOREIGN KEY (caller_id) REFERENCES cg_nodes(id),
    FOREIGN KEY (callee_id) REFERENCES cg_nodes(id)
);
```

**Round-trip verified**: Insert nodes → insert edges (via `node_id_map`) → reconstruct DiGraph from JOIN query → edges match original ✅.

**Converters** (to be implemented in S3-T2):

- `CGNode.to_row()` → `(fqn, node_type, file_path, line_number)`
- `CGNode.from_row(row)` → `CGNode(fqn=row[0], ...)`
- `CGEdge` serialization: resolve caller/callee FQN → IDs via lookup, store `(caller_id, callee_id, edge_type, confidence)`

---

## 4. PyCG Node/Edge Model Mapping

From the PyCG paper (arXiv:2103.00587):

| PyCG Concept | PyReach Equivalent | Notes |
|--------------|-------------------|-------|
| Namespaces / modules | `module_fqn` | Computed from file path relative to root |
| Function/method definitions | `CGNode` FUNCTION/METHOD | Node creation pass (S3-T3) |
| Call edges | `CGEdge` STATIC | Edge creation pass (S3-T4) |
| Dynamic calls | `CGEdge` DYNAMIC | Conservative fallback (S3-T4, R2) |
| Inheritance | `CGEdge` INHERITANCE | Class base resolution (S3-T4) |
| Import edges | `CGEdge` IMPORT | Module-level import tracking (S3-T4) |

### 4.1 PyCG features explicitly out of scope

PyCG's points-to analysis is **out of scope** for PyReach. PyCG tracks object flow through assignments to resolve indirect calls precisely. PyReach compensates with conservative heuristics:

1. **Simple assignment tracking**: If `x = SomeClass()` and later `x.method()`, resolve `x` to `SomeClass` and `x.method()` to `SomeClass.method`. Only works for direct instantiation, not for parameters/returns.
2. **Dynamic patterns**: `eval`, `exec`, `getattr`, `setattr`, `__import__`, `importlib.import_module`, `apply` → always `DYNAMIC` edge to `<DYNAMIC>` sentinel with confidence 0.5.
3. **Unresolved names**: Name not in symbol table → `<UNRESOLVED>` sentinel with confidence 0.3.
4. **`*args`/`**kwargs` on unresolved**: Flag as dynamic.

**Conservative over-approximation (R2)**: Any path containing a `DYNAMIC` edge → `POTENTIALLY_REACHABLE` (never `NOT_REACHABLE`). This is the primary false-negative mitigation.

---

## 5. API Quick Reference

```python
import networkx as nx

# Creation
G = nx.DiGraph()  # NOT nx.Graph, NOT nx.MultiDiGraph

# Nodes
G.add_node("fqn", node_type="FUNCTION", file_path="...", line_number=1)
G.add_nodes_from([("a", {...}), ("b", {...})])
G.nodes["fqn"]  # → attribute dict
G.nodes["fqn", "node_type"]  # → "FUNCTION" (direct key access)
list(G.nodes)  # → ["fqn1", "fqn2", ...]
G.number_of_nodes()

# Edges
G.add_edge("caller", "callee", edge_type="STATIC", confidence=1.0)
G.add_edges_from([("a", "b", {...}), ("b", "c", {...})])
G.edges["caller", "callee"]  # → attribute dict
G.get_edge_data("caller", "callee")  # → dict or None
list(G.edges(data=True))  # → [("caller", "callee", {...}), ...]

# Queries
list(G.successors("fqn"))  # → outgoing neighbors
list(G.predecessors("fqn"))  # → incoming neighbors
nx.has_path(G, "a", "b")  # → bool
nx.shortest_path(G, "a", "b")  # → list[str]
nx.single_source_shortest_path(G, "entry")  # → dict[str, list[str]]

# Subgraph
subg = G.subgraph(["fqn1", "fqn2"])  # → DiGraph view

# Serialization
data = nx.node_link_data(G)  # → dict (JSON-serializable)
G2 = nx.node_link_graph(data)  # → DiGraph round-trip
json_str = json.dumps(data)

# Info
G.number_of_nodes()
G.number_of_edges()
G.is_directed()  # → True for DiGraph
```

---

## 6. 10k-Node Benchmark Result

```
Build time: 296.99ms
Node count: 10000
Edge count: 9999
Peak memory: 9.84 MB
has_path(node_00000, node_09999): True
```

Conclusion: NetworkX DiGraph handles 10k nodes comfortably. Memory pressure would appear at much larger graphs (100k+), which is beyond the scope of typical microservice scans. If it does appear, the R1 mitigation (lazy library loading, pruning, `--max-depth` reduction) applies.

---

## 7. Self-Check

- [x] Can build, traverse, and serialize DiGraphs
- [x] Understands PyCG node/edge types and PyReach equivalents
- [x] Node-identity decision recorded and frozen for S3-T2
- [x] Depth-limited BFS prototype verified on cyclic graphs
- [x] Serialization round-trip (JSON + SQLite) demonstrated
- [x] 10k-node benchmark completed
- [x] `nx.Graph` vs `nx.DiGraph` vs `nx.MultiDiGraph` tradeoffs understood
- [x] `all_simple_paths` exponential risk noted and avoided

---

*Document version: 1.0*
*Date: 2026-10-01*
*Status: Complete — ready for S3-T2*
