# S3-T5 — Implement bounded reachability BFS (max depth k=5) with memoization

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 12 h |
| Dependencies | S3-T2, S3-T3, S3-T4 |
| Related docs | `06-ast-and-callgraph-engine.md` §3.2, §3.3, §3.4; `02-system-architecture.md` §Reachability Analyzer; `10-risk-and-contingency-plan.md` §2 R1, R2 |

## Purpose

Determine, for each vulnerable symbol, whether an application entry point can reach it within
`k` hops. This is the analytical heart of PyReach: false negatives here defeat the product's
purpose, so the algorithm must be iterative (no recursion-limit issues), bounded (R1), and
cycle-safe.

## Preconditions

- Call graph built (S3-T3/T4).
- Entry points available (S3-T7 may land in parallel; use a stub list for early tests).
- `Vulnerability` / `ReachabilityResult` contracts from spec §3.4/§3.5.

## Essential Sub-tasks

### 5.1 Implement the bounded traversal primitive (3 h)

In `pyreach/reachability/analyzer.py`:

```python
@dataclass
class TraversalOutcome:
    status: ReachabilityStatus
    paths: list[list[str]]
    encountered_dynamic: bool
```

`_traverse(graph, entry, target, max_depth) -> TraversalOutcome`:

- **Iterative BFS** with an explicit `collections.deque` (never recursion; spec §Security).
- Queue entries: `(node, path, depth)`.
- `visited` set prevents cycles and repeated expansion.
- Stop expanding when `depth > max_depth`.
- When `node == target`: record `path + [target]` and mark reachable.
- While expanding, if any outgoing edge is `DYNAMIC` (or leads to a `<DYNAMIC>`/`<UNRESOLVED>`
  sentinel), set `encountered_dynamic = True`.
- Bound path collection to at most `N` (e.g. 5) shortest paths to keep output small.

### 5.2 Implement per-symbol analysis (2.5 h)

```python
def analyze_reachability(
    graph: nx.DiGraph,
    entry_points: list[str],
    vulnerable_symbols: list[str],
    max_depth: int = 5,
) -> dict[str, ReachabilityResult]: ...
```

- For each symbol:
  1. If symbol not in the graph at all -> candidate `NOT_REACHABLE` (but still check
     "vulnerable package imported?" in 5.3).
  2. Try each entry point; first `REACHABLE` wins and short-circuits.
  3. If no static reach but some traversal encountered a dynamic/unresolved edge on a path
     that could lead to the symbol -> `POTENTIALLY_REACHABLE`.
  4. Else `NOT_REACHABLE`.
- Populate `entry_points_reached`, `paths`, and a human-readable `reasoning` string.

### 5.3 Instance-level reachability fallback (2 h)

Library symbols often cannot be resolved exactly (e.g. `Session.request` reached through an
instance). Provide a **symbol-prefix** fallback:

- If the exact symbol node is absent, look for any graph node whose FQN is a suffix/prefix
  match (e.g. symbol `requests.sessions.Session.request`, node `requests.api.get` is a
  different symbol -> no).
- More importantly: if the vulnerable *package* is imported somewhere in the application
  module set, and there is any path to a node in that package, classify as
  `POTENTIALLY_REACHABLE` (conservative, R2). Record `reasoning="package imported but exact
  symbol path not resolved"`.
- If the package is never imported -> `NOT_REACHABLE` (decision matrix row 4).

### 5.4 Implement memoization (2 h)

- Per-run cache keyed by `(entry, target, max_depth)` -> `TraversalOutcome`.
- Additional cache `package_imported: dict[str, bool]` to avoid rescanning module sets.
- Expose `clear_cache()` for tests.
- Document that the cache is in-memory only and invalidated between runs (cross-run cache is
  the SQLite `reachability_results` table, used in Sprint 4 if time permits).

### 5.5 Cycle and performance handling (1 h)

- Verify on a mutually recursive `A -> B -> A` graph that traversal terminates and still finds
  targets up to `max_depth`.
- Benchmark: 100-node graph must complete in `<100 ms` (roadmap acceptance criterion).
- Use `tracemalloc` in a performance test to assert graph+analysis memory stays bounded
  (R1 monitoring).

### 5.6 Write tests (1.5 h)

Create `tests/unit/reachability/test_analyzer.py` (fixture `simple_graph` from
`08-testing-strategy.md` §4.4):

| Test | Setup | Expected |
|------|-------|----------|
| `test_reachable_direct` | path length 2 | `REACHABLE`, path recorded |
| `test_not_reachable` | no edge | `NOT_REACHABLE` |
| `test_potentially_reachable_dynamic` | DYNAMIC edge on path | `POTENTIALLY_REACHABLE` |
| `test_depth_limit_exceeded` | path length 6, k=5 | `NOT_REACHABLE` |
| `test_cycle_handling` | A->B->A | terminates |
| `test_memoization` | query twice | cache hit (spy) |
| `test_package_imported_fallback` | symbol missing, pkg imported | `POTENTIALLY_REACHABLE` |
| `test_package_not_imported` | pkg absent | `NOT_REACHABLE` |
| `test_performance_100_nodes` | 100-node graph | `<100 ms` |
| `test_paths_are_short_and_bounded` | dense graph | <= N paths |

## Deliverables

- `pyreach/reachability/analyzer.py`
- `pyreach/reachability/__init__.py`
- `tests/unit/reachability/test_analyzer.py`

## Acceptance Criteria

- Completes on 100-node graph in <100ms; handles cycles gracefully. ✅ (roadmap S3-T5)
- All classification decision-matrix rows from `06-...md` §4.2 implemented.
- Iterative only; no recursion-depth failures on deep chains.

## Verification

```bash
uv run pytest tests/unit/reachability/test_analyzer.py -q
uv run pytest tests/unit/reachability --cov=pyreach.reachability --cov-report=term-missing
```

## Edge Cases & Pitfalls

- A target may be an entry point itself (depth 0) -> `REACHABLE`.
- Multiple equal-length paths: return a bounded, deterministic subset (sort paths).
- `<DYNAMIC>`/`<UNRESOLVED>` sentinels must never be treated as real targets.
- Guard against `max_depth < 0`; validate in the CLI/config layer.
- Self-loops and duplicate edges (already collapsed) must not double-count depth.

## Risks / Scope Cuts

- **R1**: default `k=5`; if performance fails, reduce default to 3 (documented precision
  trade-off in `10-...md` §2 R1).
- **R2**: never downgrade a dynamic-adjacent symbol to `NOT_REACHABLE`.

## Definition of Done

- [ ] Analyzer + tests merged.
- [ ] 100-node <100ms benchmark green.
- [ ] Cycle and depth-limit tests pass.
- [ ] Memoization proven by test.
