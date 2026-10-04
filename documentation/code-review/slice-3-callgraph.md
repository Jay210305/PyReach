# Slice 3 — Call graph

- Scope: `pyreach/callgraph/`
- Diff: `git diff c03e073...HEAD -- pyreach/callgraph` (888 lines: `__init__.py`, `nodes.py`, `edges.py`, `engine.py`)
- Spec: `documentation/implementation/sprint-3-callgraph-reachability/` S3-T1..T4 (T5..T8 belong to slice 4)
- Commits: e5a5b3b, 1299c81 ("Sprint 3 completed")
- Date: 2026-10-03

## Standards

### Hard violations (documented standards)

1. **AGENTS.md §11 "no comments unless a non-obvious algorithm demands one"** — pervasive
   what-comments: `engine.py:115-117,120,126,132,198,213-214,244,289-290,701,706,717`.
   Worse, several are **wrong or contradictory**:
   - `engine.py:151-152`: two consecutive lines contradict each other — *"don't track
     enclosing for nested functions"* immediately followed by *"We need to track
     enclosing for nested functions"*.
   - `engine.py:164`: "Resolve bases via symbol table" — the code does no symbol-table
     resolution, it copies raw names.
   - `edges.py:47-50`: stale TODO ("S3-T3 will document first-wins or max-confidence
     policy") — that policy is already implemented/documented in
     `engine.py:_add_graph_edge`.
2. **AGENTS.md §6 NodeType contract** — `engine.py:704` adds nodes with
   `node_type="SENTINEL"`, outside the documented
   `Literal["FUNCTION","METHOD","CLASS","LAMBDA"]` and bypassing `CGNode` validation.
   Then `engine.py:604-605` fabricates `CGNode(fqn="<DYNAMIC>")` with default
   `node_type="FUNCTION"` for `CGEdge` results — the returned edges carry nodes that
   misrepresent sentinels as functions. Sentinel over-approximation itself is
   spec-correct; the contract distortion downstream is not.
3. **AGENTS.md §3 dependency policy (networkx is a hard runtime dep)** —
   `nodes.py:10-13` / `edges.py:11-14` guard `ImportError` and set `nx = None`, while
   `engine.py:13` imports networkx unconditionally, so the guards can never usefully fire
   (**Speculative Generality**). Their fallout weakens §11 typing:
   `add_cgnode(graph: object, ...)` / `add_cgedge(graph: object, ...)`
   (`nodes.py:78`, `edges.py:43`) with runtime `assert isinstance` — asserts vanish under
   `python -O`; type the param `nx.DiGraph`.

### Judgement calls (baseline smells)

4. **Duplicated Code / Shotgun Surgery** — FQN conventions are split across the two
   extractors: lambda FQN built identically at `engine.py:200` and `:401`; `<locals>`
   convention at `:135` and `:363-364`. Changing a convention requires edits in both
   classes or caller/callee keys silently stop matching. Extract one shared FQN builder.
5. **Duplicated Code** — the tail cascade `elif self._has_star_args(node): DYNAMIC 0.5
   else: UNRESOLVED 0.3` repeats 5×
   (`engine.py:448-451, 483-486, 499-502, 511-514, 524-527`); `_resolve_self_call` and
   `_resolve_instance_call` are near-identical. Extract `_fallback(caller, node)`.
6. **Divergent duplicate APIs** — `add_cgedge` (last-write-wins, used only by tests) vs
   `_add_graph_edge` (precedence-based, used by engine): two edge-insertion semantics in
   one package. **Middle Man**: `engine.py:615-616` `_add_edge` purely delegates.
   Collapse into one path.
7. **Speculative Generality** — `bases` node attr (`engine.py:254`) is written but never
   read; `_build_inheritance_edges` re-walks the AST instead (`:643-656`).
8. **Data Clumps** — `_add_node`'s 10 params (`engine.py:216-228`) travel together;
   bundle into a metadata dataclass. **Primitive Obsession**: confidence magic numbers
   1.0/0.5/0.3 repeated — name them.
9. **Nit:** `# mypy: disable-error-code` directives buried mid-file (`nodes.py:16`,
   `edges.py:17`, `engine.py:15`) belong in `pyproject.toml`.

### Verified compliant

No 3.11+ syntax; DiGraph ✓; iterative BFS for hierarchy lookup ✓; error taxonomy
(`AnalysisError`) ✓.

## Spec

1. **[Missing/partial] IMPORT edges never created — plus latent `KeyError`**
   `engine.py` adds only STATIC/DYNAMIC/INHERITANCE edges. S3-T4 title: *"Implement edge
   extraction: static calls, inheritance, **imports**"*; `documentation/study/callgraph-notes.md:155`
   (their own S3-T1 deliverable) assigns it here: *"Import edges | `CGEdge` IMPORT |
   Module-level import tracking (S3-T4)"*; `06-ast-and-callgraph-engine.md:104` defines
   the type. Worse, `_EDGE_TYPE_PRECEDENCE` (`engine.py:295`) omits `"IMPORT"`, so the
   first IMPORT edge through `_add_graph_edge` raises `KeyError` at `engine.py:314`
   (`_EDGE_TYPE_PRECEDENCE[edge_type]` — direct index). Spec §4.5: *"prefer the
   highest-confidence type when an edge already exists (`STATIC` > `INHERITANCE` >
   `DYNAMIC`)"* — rule undocumented/incomplete for IMPORT.
2. **[Missing] `CGEdge` row converters (S3-T2 §2.4)**
   `edges.py` has no `to_row()`/`from_row()`; only `add_cgedge`. Spec: *"`CGEdge`
   serialization for `cg_edges` (caller_id/callee_id resolved via node ids). Keep
   converters here so S3-T5/S4 can persist/restore without duplicating logic."* The
   required test `test_edge_row_roundtrip` was quietly reinterpreted as
   `test_edge_row_roundtrip_via_graph` (`tests/unit/callgraph/test_edges.py:64`). DoD
   *"Row converters round-trip cleanly"* unmet for edges; S4 SQLite cache will now
   duplicate this logic.
3. **[Wrong] Nested lambdas: no node, orphaned bare caller**
   `NodeExtractor.visit_Lambda` (`engine.py:197-214`) doesn't recurse — comment
   *"lambdas can't contain nested defs anyway"* is false for lambdas-in-lambdas. But
   `EdgeExtractor.visit_Lambda` (`engine.py:400-404`) *does* push the inner lambda's
   scope, so `_record`→`add_edge` silently auto-creates a bare node (no `node`/`node_type`
   attrs, not in `stats`) with no link from the outer lambda → calls inside multiline
   nested lambdas are unreachable: a false negative. S3-T3 Purpose: *"Create one graph
   node for every callable … completeness here directly affects false negatives."*
4. **[Partial] `bases` metadata unresolved**
   `engine.py:166-172` appends raw `base.id`. Spec §3.4: *"record `bases` (**resolved via
   the symbol table where possible**) as node metadata"*. (INHERITANCE edges do resolve
   — `engine.py:625-656` — so metadata is just inconsistent dead weight.)
5. **[Nit] Nested-class dedup data loss**
   Every `ClassDef` gets `m.{name}` (`engine.py:162`); two *distinct* same-named nested
   classes collapse first-wins (`engine.py:229`). §3.2's *"keep the first"* assumed
   redefinitions, not different entities.
6. **[Nit] Scope creep**
   Optional-import guards (`nodes.py:10-13`, `edges.py:11-14`) despite networkx being a
   mandatory runtime dep (AGENTS.md §3); sentinel attr `node_type="SENTINEL"`
   (`engine.py:704`) is outside the §6 `NodeType` contract.

### Conformant

No `compute_fqn` helper exists in S2, so `_callable_fqn` is not a §3.2 reuse violation.
Tests otherwise cover the §3.6/§4.6 tables well.

## Summary

- Standards: 9 findings — worst: wrong/contradictory comments plus `SENTINEL` node type
  outside the §6 contract (`engine.py:704`, `:604-605`).
- Spec: 6 findings — worst: IMPORT edges never created with a latent `KeyError` on first
  IMPORT insertion (`engine.py:295,314`); nested-lambda gap is a false negative
  (`engine.py:197-214` vs `:400-404`).
