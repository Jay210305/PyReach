# Code Review Remediation Log

Records the corrections applied to every finding reported in the four slice reports
(`slice-1-data-foundation.md` … `slice-4-reachability.md`). Each finding is listed with
the resolution and the primary identifiers touched. Findings marked *"left as-is"* were
deliberately not changed (benign per the report, or out of scope).

Date of remediation: 2026-10-04.

---

## Slice 1 — Data foundation

Scope: `pyreach/parsers/`, `pyreach/osv/`, `pyreach/db/`.

### Hard violations

- **`osv/mapper.py` missing / layering inversion** — created `pyreach/osv/mapper.py`
  owning the `Vulnerability` contract, the new frozen `AffectedSymbol` dataclass,
  `is_version_affected`, and `VulnerabilityMapper.find_by_package_and_version`.
  `db/repositories.py` now only persists (`upsert`, `replace_symbols`) and no longer
  imports from `parsers`.
- **`last_affected` treated as exclusive `fixed`** — added
  `AffectedSymbol.version_fixed_inclusive` and an `is_version_affected(..., fixed_inclusive)`
  parameter; `last_affected` is now inclusive (`v > fixed` → not affected). Persisted via a
  new `affected_symbols.version_fixed_inclusive` column.
- **Comments where docstrings suffice** — removed the two flagged comments in
  `manifest.py` and folded the rule into docstrings.

### Judgement calls

- **Duplicated `include_non_pypi` block (×3)** — extracted `_add_non_pypi()`.
- **Symbol-aggregation loop duplicated** — moved lookup into `VulnerabilityMapper`; the
  parser keeps only the informational summary.
- **Speculative `ParserResult` / unused `supports()`** — `ParserResult` is now used in
  `parse()` signatures; `select_manifest_parser` dispatches via `supports()`.
- **Data clumps** — the `(symbol, introduced, fixed)` triple became `AffectedSymbol`.
- **Nits** — `iter_osv_records` yields `dict | None`; `get_db_connection` wraps only
  `sqlite3.Error`; `_NETWORK_SCHEMES` constant in the importer.

### Spec findings

- **`last_affected` inclusive (critical)** — fixed as above.
- **Multi-range overwrite (critical)** — `extract_affected` emits one `AffectedSymbol`
  per `introduced → fixed/last_affected` pair.
- **CVSS vector string never parsed (critical)** — Decimal-based CVSS v3.x base-score
  calculator (`_cvss31_base_score`) with v3→v4→v2 priority.
- **`versions[]` ignored** — honored as inclusive exact-version points when no ranges.
- **JSON-array dumps unsupported** — `iter_osv_records` detects and streams arrays.
- **Incremental watermark never persisted** — `sync_metadata` table + `skipped_up_to_date`
  bucket; watermark written after a full pass.
- **No batch commits / perf test** — commit every 1000 records +
  `test_importer_performance.py` (10k, `@pytest.mark.performance`).
- **`-r` skipped silently** — `logger.warning` (documented choice: skip, no recursion).
- **`published` date part only + malformed classification** — `_date_part()` +
  `is_pypi_record` routing (no-`id` records → `skipped_malformed`).

### Left as-is

- "Scope creep (benign)" items (extra pip flags, `DatabaseError(OSVError)`, upsert
  columns) — the report marked them benign.

---

## Slice 2 — AST engine

Scope: `pyreach/ast/`, `pyreach/loaders/`.

### Hard violations

- **`resolver.py,cover` tracked artifact** — `git rm`'d and added `*,cover` to
  `.gitignore`.
- **"what" comments restating code** — removed/folded all flagged comments.
- **Unguarded reads in `build_file`** — added `ASTBuilder._is_within_roots()` (defense in
  depth) so `build_file` refuses files outside `module_root`/`package_root`.

### Judgement calls

- **RECORD vs `dist.files` inference duplicated** — extracted `_infer_top_level()`.
- **Windows/lowercase layout duplicated** — extracted `_venv_site_packages()` and looped
  over `("Lib", "lib")`.
- **Dead `drop_count` condition** — removed in the `_resolve_level` rewrite.
- **`iter_nodes` docstring vague/wrong** — corrected to "breadth-first via `ast.walk`".
- **mtime cache nit** — left as-is (spec-mandated `(path, mtime)` single-run cache).

### Spec findings

- **`__init__.py` relative imports one level too high (critical)** — added
  `_package_fqn()`/`_is_package_module()` so `_resolve_level` drops `level-1` components
  from the *package* FQN; `relative_pkg/__init__.py` now resolves `utils →
  relative_pkg.sibling.utils`.
- **`resolve_name` missing local-binding fallback** — added `_is_top_level_binding()`.
- **`self`/`cls` not delegated** — added `resolve_method_chain(chain, class_fqn)` helper.
- **Builtins marked resolved** — `resolve_chain` now returns `resolved=False` for
  builtins.
- **Dotted `module_binding` missing** — `import a.b.c` now also records `a.b.c → a.b.c`.
- **Pipeline never populates symbol tables** — `ASTBuilder.build_all` builds the
  `ModuleIndex` and runs `SymbolTableBuilder` over the results.
- **`PackageResolver` gaps** — `*.egg-link` support, `sys.path` site-packages fallback in
  `detect_site_packages` (with a WARNING when no project venv is found).

### Left as-is

- `utf-8-sig` vs `utf-8`, extra `.ruff_cache`/`.eggs` defaults, small corpus files — all
  marked benign/documented.

---

## Slice 3 — Call graph

Scope: `pyreach/callgraph/`.

### Hard violations

- **Wrong/contradictory comments** — removed the self-contradicting
  `engine.py:151-152` pair, the false `"Resolve bases via symbol table"`, the stale
  `edges.py:47-50` TODO, and all other "what" comments.
- **`SENTINEL` node_type outside §6 contract** — sentinels now marked `is_sentinel=True`
  only; removed the `CGEdge` fabrication in `_record` that misrepresented sentinels as
  `FUNCTION`. `EdgeExtractor.extract()` returns `None` (spec §4.1).
- **Speculative networkx import guards** — removed `try/except ImportError` +
  `nx = None`; `add_cgnode`/`add_cgedge`/`add_edge` take a real `nx.DiGraph`.

### Judgement calls

- **FQN conventions split across extractors** — extracted `_lambda_fqn` and `_nested_fqn`
  (reusing `_callable_fqn`).
- **Duplicated tail cascade + near-identical self/instance methods** — extracted
  `_fallback()` and `_resolve_method_call()`.
- **Divergent edge APIs / middle man** — precedence logic moved to `edges.py::add_edge`;
  `add_cgedge` delegates; removed `_add_graph_edge` and `_add_edge`.
- **Speculative `bases` attr** — removed (inheritance resolution lives in
  `_build_inheritance_edges`).
- **Data clumps / primitive obsession** — `_NodeMeta` dataclass + `CONF_STATIC`/
  `CONF_DYNAMIC`/`CONF_UNRESOLVED` constants.
- **mypy directives buried mid-file** — moved to `disable_error_code = ["import-untyped"]`
  in `pyproject.toml`.

### Spec findings

- **IMPORT edges missing + latent `KeyError`** — added `"IMPORT"` to the precedence map
  and module-level import tracking (`visit_Import`/`visit_ImportFrom` → `module →
  imported_module` IMPORT edges).
- **`CGEdge` row converters missing** — added `to_row(node_ids)` / `from_row(row,
  nodes_by_id)`.
- **Nested-lambda false negative** — `NodeExtractor.visit_Lambda` now recurses with
  enclosing-FQN tracking.
- **`bases` metadata unresolved** — resolved by removal (dead weight).
- **Nested-class dedup** — left as-is (documented first-wins by FQN convention).

### Bonus

The rewrite also fixed a latent bug where nested functions were tagged `METHOD` instead
of `FUNCTION`.

---

## Slice 4 — Reachability

Scope: `pyreach/reachability/`.

### Hard violations

- **Bare `ValueError`** — `analyze_reachability` now raises `ConfigError` for a bad
  `max_depth`, and enforces the §7 cap (`0 ≤ max_depth ≤ 7`).
- **Symbol-keyed results dict drops colliding vulns** — results keyed by
  `(osv_id, symbol)`.

### Judgement calls (standards)

- **`_decorator_chain` recursion** — rewritten iteratively.
- **`# mypy: disable-error-code`** — removed (covered by the global
  `disable_error_code` added in slice 3).
- **`max_depth > 7` cap** — enforced at the analysis boundary.

### Baseline smells

- **Cache duplication / global mutable state** — `analyze_reachability` clears the caches
  at the start of every run (§5.4 "invalidated between runs"), removing the cross-graph
  stale-verdict hazard.
- **Comment → docstring** — `_is_main_block` docstring absorbs the quote-normalization note.

### Spec findings

- **Global "dynamic anywhere" defeats matrix row 4 (blocker)** — reordered the classifier
  so `package_imported` (row 4) precedes the dynamic signal; an unimported package is now
  `NOT_REACHABLE` even with a dynamic edge elsewhere.
- **`package_imported` reads the whole graph (blocker)** — added `imported_packages()`
  (the application import set) and an `application_imports` parameter. The helper includes
  **dynamic imports** (`importlib.import_module("pkg")` / `__import__("pkg")`) so
  `dynamic_import` stays `POTENTIALLY_REACHABLE` while `package_unused` stays
  `NOT_REACHABLE`.
- **Results keyed by symbol lose vuln association** — fixed via the `(osv_id, symbol)`
  key.
- **Memo cache not invalidated between runs** — fixed via per-run clearing.
- **Framework-decorator aliases not resolved** — `_fastapi_instance_names()` resolves
  `application = FastAPI()` (directly or via the symbol table).

### Partial / nitpicks

- **`known_fqns` dead path** — `detect_or_fail` now accepts and forwards `known_fqns`.
- **Runner detection walks nested scopes** — `_detect_module` iterates top-level
  `tree.body`.
- **`test_performance_100_nodes` lacked the `performance` mark** — marked and adjusted to
  `max_depth=7` under the new cap.
- **Slice-2 interplay (builtins/`__init__`)** — observed, not changed here.

---

## Verification

| Gate | Result |
|------|--------|
| `uv run pytest -m "not performance"` | 357 passed, 1 skipped (Windows symlink) |
| `uv run pytest -m performance` | 3 passed |
| `uv run mypy pyreach` | clean (27 files) |
| `uv run ruff check pyreach tests` | clean (scoped paths) |
| Coverage | `parsers/` ~92%, `ast/`/`loaders/` 95%, `callgraph/` 99%, `reachability/` 99% |
