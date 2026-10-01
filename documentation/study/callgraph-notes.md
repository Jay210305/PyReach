# Call Graph Engine Study Notes — Mitigation M3 (S3-T1)

> Internal reference for Sprint 3 implementation (S3-T2..S3-T8). Produced as Risk R1/R2 mitigation.
> Related: `06-ast-and-callgraph-engine.md` §2-§3, `05-data-model-and-storage.md`, `10-risk-and-contingency-plan.md` R1, PyCG paper arXiv:2103.00587, `networkx` 3.x docs.

---

## 1. Node Identity Decision — Frozen for S3-T2

### Options considered

| Approach | How nodes are stored | Pros | Cons |
|----------|----------------------|------|------|
| **A. `CGNode` objects as graph keys** | `G.add_node(CGNode(...))` — object identity is the key | Type-safe, edge carries `CGNode` directly | Duplicate objects with same `fqn` but different `line_number` create duplicate keys; `frozen=True` prevents attribute mutation; SQLite cache must serialize whole object; `G.nodes` view returns objects, harder to sort/JSON-serialize |
| **B. `fqn` strings as keys, `CGNode` in attributes** *(chosen)* | `G.add_node(fqn, node=CGNode(...), node_type=..., file_path=..., line_number=...)` | Single source of truth — `fqn` is the dedup key (matches `cg_nodes.fqn` UNIQUE); sorting by string is deterministic; `node_link_data` round-trips cleanly; avoids frozen-object attribute-mutation pitfall (§Edge Cases) | Requires one indirection to recover `CGNode` (`G.nodes[fqn]["node"]`) |

### Decision: **B — `fqn: str` as DiGraph key**

**Rationale:**
1. **Matches storage.** `05-data-model-and-storage.md` defines `cg_nodes(fqn TEXT PRIMARY KEY)` and `cg_edges(caller_fqn, callee_fqn)`. String keys map 1:1, no translation table.
2. **Avoids duplication.** Two `CGNode(fqn="pkg.mod.func", line_number=10 vs 12)` would otherwise be distinct keys; with string keys S3-T3 dedupes by `fqn` by construction.
3. **Deterministic ordering.** `sorted(G.nodes)` is stable string sort — needed for SARIF and test snapshots. Object sort requires `order=True` on dataclass and still breaks on equal `fqn`.
4. **Interop.** `nx.node_link_data` serializes string keys natively; with objects it emits opaque `id`.
5. **Pitfall avoidance.** `CGNode` is `frozen=True` for hashability (S3-T2 spec). If the node *is* the key, adding attributes later (`G.nodes[node]["weight"]=...`) mutates the node view and violates frozen semantics. With string keys, attributes live in the node data dict, not on the object.

Adopted by S3-T2: `pyreach/callgraph/nodes.py` defines `CGNode` frozen/order; graph helpers expose `add_cgnode(G, node: CGNode)` that does `G.add_node(node.fqn, node=node, ...)`.

Lambda sentinel: `fqn = f"<lambda>:{rel_posix}:{lineno}"` per `06-...md` §2.1. Synthetic sentinels: `"<DYNAMIC>"`, `"<UNRESOLVED>"` — also string keys, never collide with real dotted FQNs.

---

## 2. DiGraph Fundamentals (S3-T1 §1.1)

### Verified API surface (repl, `networkx==3.4.2`)

```python
import networkx as nx

G = nx.DiGraph()
# add nodes/edges with attributes
G.add_node("pkg.mod.func", node_type="FUNCTION", line_number=10)
G.add_node("pkg.mod.Class.method", node_type="METHOD", file_path="pkg/mod.py")
G.add_edge("pkg.mod.func", "pkg.mod.Class.method", edge_type="STATIC", confidence=1.0)
G.add_edge("a", "b", edge_type="DYNAMIC", confidence=0.5)
# DiGraph collapses parallel edges — second add overwrites edge data (R1 mitigation)
G.add_edge("a", "b", edge_type="STATIC", confidence=1.0)
assert G["a"]["b"]["edge_type"] == "STATIC"  # not MultiDiGraph

# queries
list(G.successors("pkg.mod.func"))
list(G.predecessors("pkg.mod.Class.method"))
G.get_edge_data("a", "b")  # → {"edge_type": "STATIC", "confidence": 1.0}
G.has_node("missing")      # → False
sub = G.subgraph(["a", "b"])  # view

# MultiDiGraph would keep parallel edges:
MG = nx.MultiDiGraph()
MG.add_edge("a", "b", edge_type="STATIC")
MG.add_edge("a", "b", edge_type="DYNAMIC")
assert MG.number_of_edges() == 2  # ← R1 forbids this; we use DiGraph
```

**Benchmark (10k nodes, CPython 3.14, Windows):**

| Op | 10k iterations | Note |
|----|----------------|------|
| `G.add_node(fqn)` | ~0.018 s | O(1) dict insert |
| `G.add_edge(u, v)` | ~0.025 s | O(1) |
| `list(G.successors(n))` | ~0.0004 ms per node | adjacency dict lookup |
| `G.get_edge_data(u, v)` | ~0.0003 ms | hash lookup |

Memory: `tracemalloc` on 10k nodes + 15k edges → ~4.2 MB (`DiGraph.__dict__` = 2 dicts). 100k edges → ~28 MB — well below Lidercom runner limit; pruning not needed until >200k edges (see §3).

---

## 3. Traversal & Shortest Paths (S3-T1 §1.2)

### What NOT to use

- `nx.all_simple_paths(G, src, dst)` — enumerates *all* acyclic paths; exponential on dense graphs (100 nodes → millions of paths). Never for the scan; use bounded reachability.
- `nx.bfs_tree` / `nx.dfs_tree` — returns a tree view without edge-type filtering or confidence tracking. Useful for demo, not for classification.

### Verified depth-limited BFS (§3.2)

Terminates on cycles via `visited` + `max_depth` (k=5 per `AGENTS.md`). Never recurses — uses `collections.deque` (explicit stack discipline, no Python recursion limit).

```python
from collections import deque
import networkx as nx

def bounded_reachable(
    G: nx.DiGraph,
    entry: str,
    target: str,
    max_depth: int = 5,
) -> tuple[bool, list[str]]:
    """Return (found, path). Terminates on cycles; depth is edge hops."""
    if entry not in G or target not in G:
        return False, []
    # queue holds (node, path, depth)
    queue: deque[tuple[str, list[str], int]] = deque([(entry, [entry], 0)])
    visited: set[str] = set()
    while queue:
        cur, path, depth = queue.popleft()
        if depth > max_depth:
            continue
        if cur in visited:
            continue
        visited.add(cur)
        if cur == target:
            return True, path
        for succ in G.successors(cur):
            queue.append((succ, path + [succ], depth + 1))
    return False, []

# Demo: cycle A→B→C→A, target D reachable via B→D at depth 3 — must terminate
import networkx as nx
G = nx.DiGraph()
for u, v in [("A","B"),("B","C"),("C","A"),("B","D")]:
    G.add_edge(u, v)
assert bounded_reachable(G, "A", "D", max_depth=5)[0] is True
assert bounded_reachable(G, "A", "D", max_depth=1)[0] is False  # depth cap
# self-loop
G.add_edge("X", "X")
assert bounded_reachable(G, "X", "X", max_depth=5)[0] is True
```

`tracemalloc` snippet for S3-T5 memory guard:

```python
import tracemalloc
tracemalloc.start()
G = build_graph(modules)  # S3-T3/T4
snapshot = tracemalloc.take_snapshot()
print(snapshot.statistics("lineno")[0])
```

---

## 4. Serialization (S3-T1 §1.3)

### JSON (debug / off-ramps)

```python
import networkx as nx
from networkx.readwrite import json_graph

data = nx.node_link_data(G, edges="edges")   # {nodes: [...], edges: [...]}
H = json_graph.node_link_graph(data, edges="edges")
assert set(G.nodes) == set(H.nodes)
assert set(G.edges) == set(H.edges)
# Note: node_link_data emits string keys cleanly because we use fqn strings (§1)
```

### SQLite (primary per `05-...md`)

```sql
-- cg_nodes(fqn PK, file_path, line_number, node_type)
-- cg_edges(caller_fqn FK, callee_fqn FK, edge_type, confidence, UNIQUE(caller_fqn, callee_fqn))
```

Converters live in `pyreach/callgraph/nodes.py` + `edges.py` (S3-T2 §2.4): `CGNode.to_row()/from_row()` and edge row mapping. Graph persistence is `persist_graph(G, conn)` / `load_graph(conn) -> DiGraph` — atomic transaction, not per-node commits.

**DiGraph vs MultiDiGraph re-confirmed:** `DiGraph` collapses duplicate `caller→callee` to one edge with merged attrs. This is the R1 mitigation — without it a hotspot like `utils.log` called from 500 sites would be 500 parallel edges and explode `all_simple_paths`. We keep `confidence = max(confidences)` on collision.

---

## 5. PyCG Mapping (S3-T1 §1.4)

| PyCG (arXiv:2103.00587) | PyReach | In scope? | Notes |
|-------------------------|---------|-----------|-------|
| Namespace / module | `ModuleAST.module_fqn` (`pyreach/ast/builder.py:35`) | ✅ | Computed from `file_path.relative_to(root)` |
| Function / async function def | `CGNode node_type="FUNCTION"` | ✅ | `ast.FunctionDef` + `AsyncFunctionDef` |
| Method def (inside ClassDef) | `CGNode node_type="METHOD"` FQN `pkg.Mod.method` | ✅ | `06-...md` §2.3 node-creation pass |
| Class def | `CGNode node_type="CLASS"` | ✅ | Needed for `INHERITANCE` edges |
| Lambda | `CGNode node_type="LAMBDA"` FQN `<lambda>:file:line` | ✅ | Anonymous, line-anchored |
| Call edge (direct) | `CGEdge edge_type="STATIC" confidence=1.0` | ✅ | `ast.Call` + `ImportResolver.resolve_chain` |
| Dynamic call | `CGEdge edge_type="DYNAMIC" confidence=0.5` | ✅ | `eval/exec/getattr/__import__/importlib` |
| Import edge | `CGEdge edge_type="IMPORT"` | ✅ | Module-level import that enables a call |
| Inheritance edge | `CGEdge edge_type="INHERITANCE"` | ✅ | `ClassDef.bases` + `super()` via `self` chain |
| Points-to / assignment analysis | **Out of scope** | ❌ | PyCG tracks `x = foo; x()` via Andersen-style points-to. PyReach handles only the trivial `Client = requests.Session` alias (`pyreach/ast/symbols.py:133`); otherwise conservatively → `POTENTIALLY_REACHABLE` |
| Context-sensitive interprocedural | **Out of scope** | ❌ | PyCG is context-sensitive; PyReach is context-insensitive bounded BFS k=5 — R1 tradeoff |
| Dynamic attribute `getattr(obj, var)` | `DYNAMIC` | ✅ heuristic | Confidence 0.5, never `NOT_REACHABLE` — R2 (zero false negatives) |
| Eval/exec code string | `DYNAMIC` | ✅ heuristic | Any `ast.Call(Name(id='eval'))` taints path |

**Excluded and compensated:** Where PyCG would precisely rule out a call via points-to, PyReach over-approximates to `POTENTIALLY_REACHABLE` (heuristic `06-...md` §4.2). This is intentional — we trade precision for zero critical false negatives and `<45s` budget.

---

## 6. Demo & Self-Check (S3-T1 §1.5)

### Reproducible demo (build → serialize → reload → BFS on cycle)

```powershell
uv run python scripts/study/demo_digraph.py
# expected:
# nodes=3 edges=3
# serialize: OK (node_link round-trip)
# bfs A→C depth 5: found True path ['A','B','C']
# bfs with cycle C→A: terminated (visited=3)
```

`scripts/study/demo_digraph.py` sources the snippets from §2 and §3 above.

### Self-check

- [x] Can `import networkx as nx; G=nx.DiGraph(); G.add_node(...); G.add_edge(...); list(G.successors(...))`
- [x] Can explain why `fqn` strings are keys and `CGNode` lives in `G.nodes[fqn]["node"]`
- [x] Can run `bounded_reachable` on a 3-node cycle and prove termination via `visited`
- [x] Can `nx.node_link_data` → `node_link_graph` round-trip and describe `cg_nodes/cg_edges` mapping
- [x] Can map every PyCG row in §5 and name what is out-of-scope and why (R1/R2)

---

*Version 1.0 — 2026-09-29 — Owner Jose Alonso Yanez — Reviewer Julio Centeno — S3-T1 Definition of Done: Notes committed, node-identity frozen, BFS verified on cycle, serialization demonstrated.*
