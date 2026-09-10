# S3-T6 — Implement classifier: REACHABLE / NOT_REACHABLE / POTENTIALLY_REACHABLE

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 6 h |
| Dependencies | S3-T5 |
| Related docs | `06-ast-and-callgraph-engine.md` §4 (Decision Matrix); `03-technical-specifications.md` §3.5; `10-risk-and-contingency-plan.md` §2 R2, R3 |

## Purpose

Centralize the reachability decision logic so the analyzer stays purely mechanical and the
heuristics are testable in isolation. This is where the **zero false negatives** policy (R2)
is encoded: uncertainty must always resolve upward to `POTENTIALLY_REACHABLE`.

## Preconditions

- `analyze_reachability` produces traversal outcomes (S3-T5).
- `ReachabilityStatus` literal and `ReachabilityResult` defined.

## Essential Sub-tasks

### 6.1 Implement the decision matrix (2 h)

In `pyreach/reachability/classifier.py`:

```python
class ReachabilityClassifier:
    def classify(self, evidence: TraversalOutcome, context: SymbolContext) -> ReachabilityResult: ...
```

Encode the full matrix from `06-...md` §4.2:

| Condition | Result |
|-----------|--------|
| Static path entry -> symbol, length <= k | `REACHABLE` |
| No static path; no dynamic edges in subgraph | `NOT_REACHABLE` |
| No static path; dynamic edge on any path toward symbol | `POTENTIALLY_REACHABLE` |
| Symbol's package not imported by application | `NOT_REACHABLE` |
| Package imported but call chain unresolved | `POTENTIALLY_REACHABLE` |
| `eval`/`exec` in call chain | `POTENTIALLY_REACHABLE` |
| `getattr` with variable attribute name | `POTENTIALLY_REACHABLE` |

- Encode as an explicit, ordered rule list so the precedence is obvious and testable.
- Return a `reasoning` string naming the matched rule.

### 6.2 Define `SymbolContext` (1 h)

A small dataclass passed to the classifier, decoupling it from the analyzer:

```python
@dataclass
class SymbolContext:
    symbol_fqn: str
    package_imported: bool
    exact_node_exists: bool
    dynamic_in_chain: bool
    unresolved_imports: bool
    max_depth_exceeded: bool
```

This makes every rule unit-testable without building a graph.

### 6.3 Ensure conservative ordering (1 h)

- `REACHABLE` only when a real static path is proven.
- `NOT_REACHABLE` only when **all** of the following hold: no path, exact node exists or
  package not imported, no dynamic edges in the relevant subgraph, and imports resolved.
- Any ambiguity (unresolved import, dynamic edge, depth limit reached with a possible tail)
  -> `POTENTIALLY_REACHABLE`.
- Depth-limit-exceeded alone must **not** produce `REACHABLE`; it may produce
  `POTENTIALLY_REACHABLE` if a dynamic edge is nearby, otherwise `NOT_REACHABLE` per row 4.

### 6.4 Implement reasoning strings (0.5 h)

Human-readable reasons reused verbatim in SARIF messages / text output:

- `"Static call path found from <entry> (depth N)."`
- `"Vulnerable package imported but exact symbol unresolved."`
- `"Dynamic call pattern (eval/exec/getattr/importlib) on path."`
- `"No call path found and package not imported."`
- `"Call graph depth limit k reached before resolution."`

### 6.5 Write tests (1.5 h)

Create `tests/unit/reachability/test_classifier.py`:

| Test | Context | Expected |
|------|---------|----------|
| `test_static_path_is_reachable` | path exists | `REACHABLE` |
| `test_no_path_no_dynamic` | clean | `NOT_REACHABLE` |
| `test_dynamic_forces_potential` | dynamic_in_chain | `POTENTIALLY_REACHABLE` |
| `test_package_not_imported` | not imported | `NOT_REACHABLE` |
| `test_package_imported_unresolved` | imported, unresolved | `POTENTIALLY_REACHABLE` |
| `test_eval_in_chain` | dynamic pattern | `POTENTIALLY_REACHABLE` |
| `test_getattr_variable` | dynamic pattern | `POTENTIALLY_REACHABLE` |
| `test_never_false_negative_matrix` | property-style sweep | no ambiguous case -> `NOT_REACHABLE` |
| `test_reasoning_non_empty` | any | reasoning text present |

Add a **property-style** test that iterates the cross-product of `SymbolContext` booleans and
asserts only the "all clear" combination yields `NOT_REACHABLE`.

## Deliverables

- `pyreach/reachability/classifier.py`
- `tests/unit/reachability/test_classifier.py`
- Analyzer refactored to delegate classification to `ReachabilityClassifier`.

## Acceptance Criteria

- Unit tests for all three categories; 0 false negatives on test suite. ✅ (roadmap S3-T6)
- Full matrix from `06-...md` §4.2 implemented and tested.
- Classifier has no dependency on NetworkX (pure logic).

## Verification

```bash
poetry run pytest tests/unit/reachability/test_classifier.py -q
poetry run pytest tests/unit/reachability --cov=pyreach.reachability --cov-report=term-missing
```

## Edge Cases & Pitfalls

- Do not let `depth_limit_exceeded` alone downgrade to `NOT_REACHABLE` when a dynamic edge is
  present anywhere on the frontier.
- Empty `paths` must not be reported as reachable.
- `package_imported` detection must be based on the application's imports, not the whole
  graph (which includes library nodes).
- Enum/string comparison: keep `ReachabilityStatus` as the single source of truth.

## Risks / Scope Cuts

- **R2**: this task is the primary R2 control. Do not simplify away the conservative rules.

## Definition of Done

- [ ] Classifier + tests merged.
- [ ] Property sweep proves conservative ordering.
- [ ] Analyzer delegates to classifier.
- [ ] Coverage >=85% on `reachability/`.
