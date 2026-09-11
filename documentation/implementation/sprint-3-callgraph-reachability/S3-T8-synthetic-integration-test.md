# S3-T8 — Integration test: synthetic project with known reachable/unreachable CVEs

| Field | Value |
|-------|-------|
| Sprint | 3 — Call Graph Construction and Reachability Algorithm |
| Owner | Jose Alonso Yanez |
| Effort | 6 h |
| Dependencies | S3-T3, S3-T4, S3-T5, S3-T6, S3-T7, S1-T5 (fixtures) |
| Related docs | `08-testing-strategy.md` §5.1, §8; `06-ast-and-callgraph-engine.md` §4.3 |

## Purpose

Prove the whole pipeline (parse -> graph -> entry points -> reachability -> classification) is
correct end to end on projects whose expected verdicts are known. This is the final Sprint 3
gate and the highest-value regression suite for the analysis core.

## Preconditions

- All Sprint 3 modules merged and unit-tested.
- `tests/fixtures/projects/` exists with synthetic projects.
- A small set of OSV records (from S1) or a stub advisory provider for deterministic CVEs.

## Essential Sub-tasks

### 8.1 Build five synthetic scenarios (2.5 h)

Create projects under `tests/fixtures/projects/` (mirroring `08-...md` §8):

| Scenario | Layout | Expected verdict |
|----------|--------|------------------|
| `linear_reachable` | `main.py` -> `client.fetch()` -> `vuln_lib.risky()` | `REACHABLE` |
| `transitive_unreachable` | app imports `safe_lib`, vuln symbol never called | `NOT_REACHABLE` |
| `dynamic_import` | `importlib.import_module("plugin")` -> vuln symbol | `POTENTIALLY_REACHABLE` |
| `depth_limit` | chain length 6 with `max_depth=5` | `NOT_REACHABLE` |
| `package_unused` | vuln package is a dependency but never imported | `NOT_REACHABLE` |

Each project includes:
- `requirements.txt` pinning the "vulnerable" package.
- A local stub package simulating the vulnerable library so tests need no network.
- A `README.md` describing the expected result.

### 8.2 Create a deterministic stub advisory source (1 h)

- Provide an in-memory `Vulnerability` list or a tiny SQLite fixture mapping
  `(package, version) -> symbol`, so integration tests do not depend on real CVEs.
- Keep it in `tests/fixtures/advisories.py` or a small `.sql` seed.

### 8.3 Implement the integration harness (1 h)

Create `tests/integration/test_reachability_scenarios.py`:

```python
@pytest.mark.parametrize("scenario,expected", SCENARIOS)
def test_scenario(tmp_path, scenario, expected):
    project = copy_fixture(scenario, tmp_path)
    modules = run_ast_pipeline(project)
    graph = CallGraphEngine(index).build(modules)
    entries = EntryPointDetector(modules).detect()
    results = analyze_reachability(graph, entries, [SYMBOL], max_depth=5)
    assert results[SYMBOL].status == expected
```

- Use the same library code paths for all scenarios (only the app changes) to isolate variables.

### 8.4 Add failure-diagnostic output (0.5 h)

- On assertion failure, dump the call graph edges and the discovered entry points to aid
  debugging (use `pytest` custom message / `logging`).
- Attach the computed path for `REACHABLE` cases and assert it matches the expected chain.

### 8.5 Validate accuracy target (0.5 h)

- The roadmap requires **5 synthetic scenarios with 100% accuracy**.
- Parametrize exactly 5 scenarios and assert statuses.
- Also assert no `REACHABLE` false positives: `NOT_REACHABLE` scenarios contain zero static
  paths to the symbol.

### 8.6 Performance sanity check (0.5 h)

- Measure graph build + analysis for `linear_reachable`; assert it completes under a generous
  bound (e.g. <2 s) so Sprint 4's <45 s budget stays plausible.
- Mark as `@pytest.mark.performance` if desired.

## Deliverables

- `tests/fixtures/projects/{linear_reachable,transitive_unreachable,dynamic_import,depth_limit,package_unused}/`
- `tests/fixtures/advisories.py` (stub advisory source)
- `tests/integration/test_reachability_scenarios.py`

## Acceptance Criteria

- Passes 5 synthetic scenarios with 100% accuracy. ✅ (roadmap S3-T8)
- Reachability analyzer classifies all synthetic test CVEs correctly. ✅ (Sprint 3 DoD)
- No network required; deterministic.
- `REACHABLE` path matches the documented chain.

## Verification

```bash
uv run pytest tests/integration/test_reachability_scenarios.py -q
uv run pytest tests/integration -q
```

## Edge Cases & Pitfalls

- Fixture stubs must be importable by module FQN; a malformed package layout invalidates the
  test (keep simple `__init__.py` trees).
- `dynamic_import` must genuinely involve a dynamic pattern or it will be classified
  `REACHABLE` instead.
- `depth_limit` must be exactly length 6 with k=5; off-by-one makes it `POTENTIALLY_REACHABLE`
  if any dynamic edge exists — keep the chain purely static.
- Copy fixtures to `tmp_path` so parallel `pytest-xdist` runs don't collide.

## Risks / Scope Cuts

- **R1/R2**: these scenarios encode the R2 acceptance bar. Do not weaken expected statuses to
  make tests pass; fix the engine instead.
- If time is short, keep all five but reduce each project to the minimum code needed.

## Definition of Done

- [ ] Five scenarios + stub advisories merged.
- [ ] Integration suite green with 100% accuracy.
- [ ] Diagnostics aid debugging.
- [ ] No network or real-CVE dependency.
