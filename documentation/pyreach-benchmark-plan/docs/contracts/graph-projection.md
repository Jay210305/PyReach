# Contract C-GRAPH 1.0.0 — canonical call graph

## Inputs and outputs
**Source:** PyAnalyzer `callgraph.json`, PyCG output, SWARM-CG ground truth, FASTEN stitched graph (each explicitly selected parser); PyReach internal graph **only if S0 audit confirms projection**. Do not parse SARIF findings as a complete call graph.

Proposed typed interface:
```python
@dataclass(frozen=True)
class GraphProjection:
    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]
    unresolved: tuple[str, ...]
    excluded: tuple[str, ...]
    source_format: str

def normalize_graph(raw: object, *, source_format: str, root: Path) -> GraphProjection: ...
```
Canonical symbol `module.path:Class.method` (function-level, namespaced, case-sensitive), with documented normalization for path/module roots, `__init__` and library imports. **Do not guess** whether raw graph nodes represent function object, call site, class, module; freeze a parser-specific mapping and fixture test.

## Valid / invalid
Valid normalized projection: `{"nodes":["app.main:main","pkg.worker:run"],"edges":[["app.main:main","pkg.worker:run"]],"unresolved":[],"excluded":[],"source_format":"canonical-v1"}`. Invalid: `{"edges":[["main"]]}` → `SCHEMA_INVALID` (edge must contain exactly 2 symbols). If PyReach graph inaccessible: `GRAPH_EXPORT_UNSUPPORTED` with no graph scores (not an empty graph).

## Comparison semantics
Exact directed pair matching for mutually resolvable namespace IDs. `TP=|prediction∩reference|`; `FP=|prediction-reference|`; `FN=|reference-prediction|`; restrict eligibility **before** inspecting prediction. Every exclusion is recorded, and callgraph micro metrics use unique 233 case IDs. False negatives cannot be silently excluded after reading outcomes.

## Verification fixtures
1. One-match, one-extra-edge, one-missing-edge graph.
2. Aliased import + path normalization test.
3. Unsupported format returns structured error and no 0-F1 deception.
4. Dedupe duplicate edges and case IDs.
