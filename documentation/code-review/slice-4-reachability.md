# Slice 4 — Reachability

- Scope: `pyreach/reachability/`
- Diff: `git diff c03e073...HEAD -- pyreach/reachability` (625 lines: `__init__.py`, `analyzer.py`, `classifier.py`, `contracts.py`, `entrypoints.py`)
- Spec: `documentation/implementation/sprint-3-callgraph-reachability/` S3-T5..T8 (T1..T4 belong to slice 3)
- Commits: e5a5b3b, 1299c81 ("Sprint 3 completed")
- Date: 2026-10-04

## Standards

### Hard violations

1. **analyzer.py:158** — `raise ValueError("max_depth must be >= 0")`. AGENTS.md §12
   defines a closed error taxonomy (`PyReachError` → `ConfigError`/`AnalysisError`…); a
   bad `max_depth` is a configuration/CLI error and must raise `ConfigError`, not a bare
   `ValueError`. This will also escape the CLI's exit-code mapping (§12: config error →
   exit 2).
2. **analyzer.py:164** — `results[symbol] = _analyze_symbol(...)`. Results are keyed by
   symbol FQN, so if two vulnerabilities list the same affected symbol (common: same
   CVE-mapped helper across advisories), the second silently overwrites the first and a
   finding is lost. This contradicts §5 pipeline step 6 (per-vulnerability
   classification) and the §6 `ReachabilityResult` shape, which embeds one
   `vulnerability`. Key by `(vuln.osv_id, symbol)` or return a list.

### Judgement calls (documented standards)

3. **entrypoints.py:65-72** — `_decorator_chain` recurses
   (`return _decorator_chain(decorator.func)`). AGENTS.md §11: "Prefer iterative
   traversal over recursion." Depth is bounded by AST chain length so it's safe in
   practice, but a `while` loop like `_attr_chain` (line 53) already in the same file
   would be consistent.
4. **analyzer.py:25** — `# mypy: disable-error-code="import-untyped"` targeting
   `networkx`, which ships `py.typed`; the suppression is likely unnecessary, sits oddly
   between imports, and blanket-disables the code for the whole file. Verify and drop if
   unneeded.
5. **analyzer.py:157** — validates `max_depth >= 0` but not the §7 cap "never >7".
   Enforcing at the analysis boundary (not just CLI, Sprint 4) is cheap defense-in-depth.

### Baseline smells (judgement calls)

6. **Duplicated Code — analyzer.py:48-54 vs 106-113**: identical get→compute→store cache
   shape in `_traverse` and `_package_imported`. Also **entrypoints.py:100-112 vs
   179-186**: `_runner_target` and `_direct_call` share the same
   `Name`/`Attribute`→`_attr_chain(...)→chain[-1]` extraction; `_direct_call` is a subset
   of `_runner_target`. Extract once.
7. **Global mutable state — analyzer.py:37-38**: module-level caches keyed without graph
   identity; a changed graph between calls without `clear_cache()` yields stale verdicts.
   Documented, but a `ReachabilityAnalyzer` instance holding the caches would remove the
   cross-test hazard.
8. **Nit — entrypoints.py:95-96**: comment explains *why* (quote normalization) —
   acceptable under §11, but could be a docstring line.

### Verified compliant

Iterative BFS (§11), `ReachabilityResult` matches §6, classifier decision matrix matches
doc 06 §4.2 (depth-limit → `NOT_REACHABLE` is spec-sanctioned), `ConfigError` on empty
entry points (§12), Python 3.10-compatible syntax throughout.

## Spec

### Implemented but wrong

1. **[Blocker] Global "dynamic anywhere" defeats decision-matrix row 4.**
   `analyzer.py:73-102` sets `encountered_dynamic` for any DYNAMIC edge in the entry's
   whole frontier, and `classifier.py:69-70` checks it *before* `package_imported`.
   Spec S3-T5 §5.2: *"dynamic/unresolved edge **on a path that could lead to the
   symbol**"*; S3-T6 §6.1 row: *"Symbol's package not imported by application |
   NOT_REACHABLE"*. One dynamic edge anywhere makes every unimported-package symbol
   `POTENTIALLY_REACHABLE`. Conservative (no false negatives) but violates the matrix
   and will drown CI gates. `_unresolved_imports` (`analyzer.py:116-124`) is the same
   global proxy.
2. **[Blocker] `package_imported` uses the whole graph, not application imports.**
   `analyzer.py:106-113`. S3-T6 Pitfalls: *"package_imported detection must be based on
   the application's imports, not the whole graph (which includes library nodes)."* Once
   Sprint 4 loads library ASTs, row 4 can never fire. Also S3-T5 §5.3's condition *"and
   there is any path to a node in that package"* is unchecked, and the symbol
   prefix-match fallback (*"look for any graph node whose FQN is a suffix/prefix
   match"*) is missing entirely.
3. **[Improvement] Results keyed by symbol lose vulnerability association.**
   `analyzer.py:162-166`: two `Vulnerability` objects sharing an affected symbol
   silently overwrite; AGENTS.md §6 makes `ReachabilityResult` per-vulnerability. The
   spec signature was `vulnerable_symbols: list[str]` (S3-T5 §5.2) — switching to
   `list[Vulnerability]` while keeping a symbol-keyed dict creates the collision.
4. **[Improvement] Memo cache isn't invalidated between runs and ignores graph
   identity.** `analyzer.py:37-54`, key `(entry, target, max_depth)`. S3-T5 §5.4:
   *"cache is in-memory only and invalidated between runs."* Two graphs in one process
   (exactly what the integration suite does) get stale outcomes unless callers remember
   `clear_cache()`.
5. **[Improvement] Framework-decorator aliases not resolved via symbol table.**
   `entrypoints.py:36-37,75-83` matches literal bindings `{app, router, api}`. S3-T7
   Pitfalls: *"Decorator objects may be imported aliases… resolve via the symbol table
   before comparing."* `application = FastAPI()` is missed — under-detection, contra
   *"Prefer over-detection"* (R2).

### Partial / missing

6. `console_scripts` detection (S3-T7 rule 5) not implemented — documented in the
   docstring; spec said *"best-effort; document"*, borderline acceptable.
7. `resolve_entry_points` gained an unspecced `known_fqns` param; since
   `detect_or_fail` never passes it, the required *"log a WARNING but keep it"* path is
   dead in real flows (`entrypoints.py:224-225`).

### Nitpicks

- Nit: `entrypoints.py:166,179-186`: `mod.func()` inside a `__main__` block yields wrong
  FQN `<module>.func`; runner detection walks nested scopes though spec says
  *"Module-level"*.
- Nit: `test_performance_100_nodes` (test_analyzer.py:129) uses tracemalloc but lacks
  the `performance` mark AGENTS.md §10 requires.
- Slice-2 interplay: builtins-as-resolved reduces `<UNRESOLVED>` sentinels, muting
  finding 1's proxy; `__init__.py` over-high resolution can create false prefix matches
  in `_package_imported`.

## Summary

- Standards: 8 findings — worst: bare `ValueError` instead of `ConfigError`
  (`analyzer.py:158`, breaks §12 exit-code mapping); symbol-keyed results dict silently
  drops colliding vulnerabilities (`analyzer.py:164`).
- Spec: 9 findings — worst (blockers): global "dynamic anywhere" flag defeats matrix row
  4 (every unimported symbol becomes POTENTIALLY_REACHABLE); `package_imported` reads the
  whole graph instead of application imports, so row 4 can never fire once library ASTs
  load.
