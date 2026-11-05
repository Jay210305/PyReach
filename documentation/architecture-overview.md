# PyReach Architecture Overview

*For a new contributor or a Lidercom engineer maintaining the runner.
Synthesizes `02-system-architecture.md`; describes the code **as shipped**.*

## 1. What the system does

PyReach answers one question: **is this known-vulnerable dependency symbol
actually reachable from this application's entry points?** It never executes
project code — it parses manifests, queries a local advisory database,
parses source into ASTs, builds a call graph, and classifies each finding as
`REACHABLE`, `POTENTIALLY_REACHABLE`, or `NOT_REACHABLE`, emitting SARIF
v2.1.0 plus a CI-gating exit code.

## 2. Component diagram

```text
Input Layer                 Analysis Core                  Output Layer
-----------                 -------------                  ------------
requirements.txt  --->  Manifest Parser  -------+
Pipfile.lock            (parsers/manifest.py)   |
Source tree (.py) --->  Source Loader           |       SARIF Serializer
(site-packages)         (loaders/source.py)     |       (output/sarif.py) ---> .sarif
                        Package Resolver        +--->   CLI Reporter  ⌄----> stdout (text)
                        (loaders/packages.py)   |       (cli.py)             .json file
OSV SQLite DB   --->  OSV Mapper                |
(advisories)            (osv/mapper.py)         |
                        AST Builder             |
                        (ast/builder,symbols,   |
                         resolver.py)           |
                        Call Graph Engine       |
                        (callgraph/, NetworkX   |
                         DiGraph)               |
                        Reachability Analyzer   |
                        (reachability/)  -------+

Orchestration: cli.py run_scan() · Config: config.py · Errors: exceptions.py
```

## 3. Data flow pipeline (6 steps, `02-system-architecture.md`)

1. **CLI invocation** — `cli.py:main()` parses args (stdlib `argparse`),
   `run_scan()` resolves `.pyreach.yml` + flags via `config.py`.
2. **Manifest + advisories** — `RequirementsTxtParser`/`PipfileLockParser`
   emit `Dependency` (PEP 503 names); `VulnerabilityMapper` returns the
   `Vulnerability` records whose version ranges contain the installed version.
3. **Sources + library code** — `SourceLoader` discovers app `.py` files;
   `ASTBuilder` parses them (single bad files warn-and-skip, never abort);
   `PackageResolver` locates installed distributions and the defining module
   of each vulnerable symbol is parsed too (best-effort).
4. **Call graph** — `CallGraphEngine.build()` (three passes: nodes,
   inheritance, edges) produces one `networkx.DiGraph` keyed by FQN string;
   edges are `STATIC`/`DYNAMIC`/`INHERITANCE`/`IMPORT` with confidence.
5. **Reachability** — bounded iterative BFS (`max_depth`, default 5, never
   > 7) from each entry point (`EntryPointDetector` + `-e` overrides);
   `ReachabilityClassifier` applies the conservative decision matrix.
6. **Output** — `SarifBuilder` (SARIF, deterministic order), JSON summary,
   or human text; exit code `0` / `1` / `2`.

## 4. Package/module map (as shipped, `03-technical-specifications.md` §2)

| Module | Role |
|--------|------|
| `pyreach/cli.py` | Argparse, `run_scan` orchestration, text/JSON formatters, `ExitCode` |
| `pyreach/config.py` | `.pyreach.yml` + user-global loader, CLI>file>global>defaults merge |
| `pyreach/exceptions.py` | `PyReachError` → `ConfigError`/`ParseError`/`OSVError`/`AnalysisError`/`OutputError` |
| `pyreach/parsers/manifest.py` | `Dependency`, both manifest parsers, `select_manifest_parser` |
| `pyreach/parsers/osv_json.py` | OSV JSON record → advisory parsing (ingest side) |
| `pyreach/loaders/source.py` | `SourceLoader` discovery with default + user ignores |
| `pyreach/loaders/packages.py` | `PackageResolver`, `detect_site_packages` (venv → sys.path) |
| `pyreach/osv/mapper.py` | `Vulnerability` contract, version-range matching |
| `pyreach/osv/importer.py` | Bulk JSONL → SQLite ingestion (`sync_osv`) |
| `pyreach/ast/builder.py` | `parse_source`, `ModuleAST`, cached per-file builds |
| `pyreach/ast/symbols.py` | `SymbolTableBuilder` (local names, imports) |
| `pyreach/ast/resolver.py` | `ModuleIndex`, `ImportResolver` (alias → FQN) |
| `pyreach/callgraph/nodes.py` | Frozen `CGNode` + SQLite row converters |
| `pyreach/callgraph/edges.py` | Frozen `CGEdge`, deterministic dedup on `(confidence, type)` |
| `pyreach/callgraph/engine.py` | `NodeExtractor`, `EdgeExtractor`, `CallGraphEngine` |
| `pyreach/reachability/contracts.py` | `ReachabilityResult`, `TraversalOutcome`, `MAX_PATHS` |
| `pyreach/reachability/analyzer.py` | Bounded BFS + memoization, `imported_packages` |
| `pyreach/reachability/classifier.py` | Pure decision matrix (no NetworkX) |
| `pyreach/reachability/entrypoints.py` | Auto-detect, `resolve_entry_points`, `detect_or_fail` |
| `pyreach/output/sarif.py` | SARIF dataclasses, `RULE_CATALOG`, `SarifBuilder`, schema loader |
| `pyreach/db/` | `connection.py` (context manager), `repositories.py`, `schema.sql` |

Note: human-text/JSON formatters live in `cli.py` (no separate
`output/summary.py`); config lives in `config.py`, not `cli.py`.

## 5. Key design decisions

- **Local-first.** The DB is the only data input and it is a file. The scan
  path performs zero network I/O (audited S4-T7); only DB provisioning moves
  data. Consequence: results are reproducible offline, at the cost of DB
  freshness (weekly cron owns that).
- **SQLite for advisories.** Indexed `package_name`/`symbol_fqn` lookups,
  single-file deployment to runners, WAL mode. Call-graph caching tables
  exist in schema but the hot path is in-memory (flag `--cache` reserved).
- **NetworkX `DiGraph`, FQN-string keys.** Direction matters (caller →
  callee), parallel edges collapse deterministically, string keys align with
  the `cg_nodes.fqn` cache key and keep BFS cheap. Never `MultiDiGraph`,
  never recursion (iterative `deque` BFS).
- **SARIF v2.1.0 with `properties`-only custom data.** Risk R3 (dashboard
  rejection) is contained: strip optional fields, never top-level ones;
  `jsonschema` validates every test output against the cached OASIS schema.
- **Bounded, memoized traversal.** `max_depth` default 5, hard cap 7;
  per-run caches cleared per scan; `MAX_PATHS = 5` keeps SARIF small;
  `all_simple_paths` is banned (exponential on dense graphs).

## 6. Conservative over-approximation (R2, plain language)

When the analyzer **cannot prove** a symbol is unreachable, it must say
`POTENTIALLY_REACHABLE`, never `NOT_REACHABLE`. In practice:

- `eval`/`exec`/`getattr`/`importlib`/unresolved imports emit `DYNAMIC` edges
  to sentinel nodes; any such edge on the frontier escalates the verdict.
- A package imported anywhere (statically *or* dynamically) whose exact
  symbol node is missing still escalates.
- Package-name comparison is PEP 503-normalized (`vuln-lib` ≡ `vuln_lib`),
  so naming variants cannot silently read as "not imported".
- Depth-limit cutoffs report `POTENTIALLY_REACHABLE` because traversal has
  not inspected the remaining path.

The price is false *positives* (noise), never false *negatives* on the
reachable question. `--include-potentially` lets CI decide whether noise
blocks the pipeline.

When the bounded search runs out of depth, the classifier reports
`POTENTIALLY_REACHABLE`. Raising `--max-depth` (cap 7) may resolve that
uncertainty. Installed distribution metadata supplies top-level import names,
so wildcard advisories for packages such as `PyYAML` also recognize `yaml`.

## 7. Performance model and limits

Measured on the R4 replica (S4-T7, `documentation/validation/`):
micro fixture ≈ 0.2 s cold; 31-module/421-node/808-edge tree ≈ 1.2 s
pipeline (≈ 1.6 s end-to-end CLI), 7 MB peak. Budget: < 45 s, < 2 GB,
SARIF < 5 MB, DB age < 7 days. Cost drivers: file count (parse), edge
density (BFS fan-out), and findings count (SARIF size). Levers, in order:
`--max-depth 3`, `--exclude`, more RAM. Guarded by
`tests/integration/test_scan_benchmark.py` (performance-marked).

## 8. Where to extend

- **New manifest parser** (e.g. `poetry.lock`): implement the
  `ManifestParser` protocol (`supports` + `parse`) in `parsers/manifest.py`;
  selection is filename-driven, no CLI change needed.
- **New output format**: add a branch in `cli.py:emit_output()` next to
  `build_json_document()`; reuse `_symbol_file_line()` for locations.
- **New entry-point rule** (framework): extend `_detect_module()` in
  `reachability/entrypoints.py`; detectors are additive and sorted.
- **New SARIF rule/level**: append to `RULE_CATALOG` in `output/sarif.py`
  (`ruleIndex` follows insertion order); custom data goes in `properties`.
- **New config key**: extend `PyReachConfig` + `_TOP_LEVEL_KEYS` in
  `config.py` and document it here and in `user-manual.md` (strict mode
  rejects anything unlisted).
