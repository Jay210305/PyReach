# System Architecture

## Architectural Drivers

1. **Local-First**: All computation must occur on the local filesystem / CI runner. No network calls during analysis.
2. **Speed**: Scan must complete in <45s for typical microservices.
3. **Accuracy**: Zero critical false negatives; conservative over-approximation for uncertainty.
4. **Interoperability**: SARIF v2.1.0 output for universal CI/CD and IDE consumption.
5. **Extensibility**: Modular pipeline stages allow future manifest parsers or output formats.

## High-Level Component Diagram

```
+------------------+      +------------------+      +------------------+
|   Input Layer    | ---> |  Analysis Core   | ---> |   Output Layer   |
+------------------+      +------------------+      +------------------+
|                  |      |                  |      |                  |
| - requirements.  |      | - Manifest Parser|      | - SARIF v2.1.0   |
|   txt            |      | - OSV Mapper     |      |   Serializer     |
| - Pipfile.lock   |      | - AST Builder    |      | - CLI Reporter   |
| - Source Code    |      | - Call Graph     |      | - Exit Code      |
| - site-packages  |      |   Engine (Network|      |   Controller     |
|                  |      |   X)             |      |                  |
|                  |      | - Reachability   |      |                  |
|                  |      |   Analyzer       |      |                  |
+------------------+      +------------------+      +------------------+
         |                         |                         |
         v                         v                         v
+------------------+      +------------------+      +------------------+
|  External Data   |      |  Internal Store  |      |  CI/CD / User    |
|  (Pre-loaded)    |      |  (SQLite)        |      |  Consumption     |
+------------------+      +------------------+      +------------------+
| - OSV JSON dump  |      | - Advisory DB    |      | - GitLab CI      |
|   (offline)      |      | - Call Graph DB  |      | - Local IDE      |
| - CPython stdlib |      | - Symbol Index   |      | - HTML Reports   |
|   AST schema     |      | - Cache          |      |   (future)       |
+------------------+      +------------------+      +------------------+
```

## Component Descriptions

### 1. Input Layer

**Manifest Parser**
- **Module**: `pyreach.parsers.manifest`
- **Responsibility**: Read and normalize dependency declarations from `requirements.txt` and `Pipfile.lock`.
- **Output**: Normalized list of `(package_name, installed_version, source)` tuples.
- **Edge Cases**:
  - Handle editable installs (`-e git+...`), extras (`package[extra]`), and environment markers.
  - Skip non-PyPI URLs or flag them as unresolvable.
  - Parse `Pipfile.lock` only if present and `requirements.txt` is missing (negotiable scope).

**Source Code Loader**
- **Module**: `pyreach.loaders.source`
- **Responsibility**: Discover and read all `.py` files in the target application directory, excluding `venv/`, `.tox/`, `__pycache__/`, and user-configured ignore patterns.
- **Output**: Iterator of `(file_path, source_text)` pairs.

**site-packages Resolver**
- **Module**: `pyreach.loaders.packages`
- **Responsibility**: Map parsed package names to their installed directories in the active Python environment's `site-packages`.
- **Output**: Dictionary `{package_name: package_root_path}`.

### 2. Analysis Core

**OSV Mapper**
- **Module**: `pyreach.osv.mapper`
- **Responsibility**:
  1. Query the local SQLite OSV database for advisories affecting each installed package/version.
  2. Extract affected functions/methods/symbols from the OSV `affected[].ranges[]` and `affected[].ecosystem_specific` fields.
- **Output**: List of `Vulnerability` dataclasses, each containing CVE ID, severity, affected symbols, and package reference.

**AST Builder**
- **Module**: `pyreach.ast.builder`
- **Responsibility**:
  1. Parse each `.py` file into a CPython `ast.AST` tree using the standard library `ast` module.
  2. Build a per-module symbol table mapping imported names to their fully qualified origins.
  3. Resolve aliases (`import numpy as np`, `from x import y as z`).
- **Output**: `ModuleAST` objects containing the AST tree, symbol table, and file metadata.

**Call Graph Engine (NetworkX)**
- **Module**: `pyreach.callgraph.engine`
- **Responsibility**:
  1. Traverse ASTs to identify function definitions and call sites.
  2. Create nodes for every function/method: `(module_fqn, function_name, class_name?)`.
  3. Create directed edges for every call relationship: `caller -> callee`.
  4. Handle special cases:
     - Method resolution via `self` / `cls` binding (intra-class edges).
     - Inheritance edges for overridden methods.
     - Dynamic calls (`eval`, `exec`, `getattr`, `importlib.import_module`) flagged as `DYNAMIC` edge type.
- **Data Structure**: `networkx.DiGraph` with node/edge attributes for type and confidence.

**Reachability Analyzer**
- **Module**: `pyreach.reachability.analyzer`
- **Responsibility**:
  1. Define entry points: CLI-configured root functions (e.g., `main`, FastAPI route handlers, Django views), or auto-detect `if __name__ == "__main__"` blocks.
  2. For each vulnerable symbol from OSV Mapper, perform a bounded DFS/BFS from all entry points up to depth `k=5`.
  3. Classification logic:
     - If a path exists using only `STATIC` edges: **Reachable**.
     - If no path exists and no `DYNAMIC` edges are nearby: **Not Reachable**.
     - If the symbol is involved in or near a `DYNAMIC` edge, or the call chain contains unresolved imports: **Potentially Reachable**.
- **Optimization**: Memoize reachability results per function node to avoid recomputation across multiple CVEs.

### 3. Internal Store (SQLite)

**Schema Overview**

```sql
-- Advisories table (populated from OSV JSON dump)
CREATE TABLE advisories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osv_id TEXT NOT NULL UNIQUE,        -- e.g., "GHSA-xxx" or "CVE-2023-yyyy"
    cve_id TEXT,
    package_name TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'PyPI',
    severity_score REAL,                -- CVSSv3 or CVSSv4 base score
    severity_level TEXT CHECK(severity_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    summary TEXT,
    published_date TEXT,
    aliases TEXT                        -- JSON array of alias IDs
);

-- Affected symbols table
CREATE TABLE affected_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisory_id INTEGER NOT NULL,
    symbol_fqn TEXT NOT NULL,           -- Fully qualified name, e.g., "requests.get"
    version_introduced TEXT,
    version_fixed TEXT,
    FOREIGN KEY (advisory_id) REFERENCES advisories(id)
);

-- Call graph nodes table (optional persistence for large repos)
CREATE TABLE cg_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_fqn TEXT NOT NULL UNIQUE,      -- "module.submodule.Class.method"
    file_path TEXT,
    line_number INTEGER,
    node_type TEXT CHECK(node_type IN ('FUNCTION','METHOD','CLASS','LAMBDA'))
);

-- Call graph edges table
CREATE TABLE cg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id INTEGER NOT NULL,
    callee_id INTEGER NOT NULL,
    edge_type TEXT CHECK(edge_type IN ('STATIC','DYNAMIC','INHERITANCE','IMPORT')),
    confidence REAL DEFAULT 1.0,        -- 1.0 = certain, <1.0 = heuristic
    UNIQUE(caller_id, callee_id, edge_type)
);

-- Reachability results cache
CREATE TABLE reachability_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_fqn TEXT NOT NULL,
    entry_point_fqn TEXT NOT NULL,
    result TEXT CHECK(result IN ('REACHABLE','NOT_REACHABLE','POTENTIALLY_REACHABLE')),
    max_depth INTEGER,
    path_json TEXT,                     -- JSON array of node_fqn path
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Access Patterns**
- Read-heavy during analysis; write-heavy during initial OSV ingestion.
- Indexed on `advisories.package_name`, `affected_symbols.symbol_fqn`, `cg_nodes.node_fqn`, `reachability_results.symbol_fqn`.

### 4. Output Layer

**SARIF v2.1.0 Serializer**
- **Module**: `pyreach.output.sarif`
- **Responsibility**: Convert reachability results into valid SARIF JSON conforming to OASIS SARIF v2.1.0 schema.
- **Key Mappings**:
  - Each vulnerability -> `result` object.
  - Reachability classification -> `result.properties.reachability` (custom property) or `result.level` mapping:
    - Reachable -> `error`
    - Potentially Reachable -> `warning`
    - Not Reachable -> `note` (or filtered out based on CLI flag).
  - Call path (if reachable) -> `result.codeFlows` with `threadFlow.locations`.
- **Validation**: Use `jsonschema` library in unit tests to validate against the official SARIF schema.

**CLI Reporter**
- **Module**: `pyreach.cli`
- **Responsibility**: Print human-readable summary to stdout/stderr with progress bars (optional) and final statistics.
- **Exit Codes**:
  - `0`: Analysis completed; no reachable CVEs found (or `--no-fail` flag set).
  - `1`: One or more Reachable CVEs detected (CI gate failure).
  - `2`: Configuration error, missing manifest, or parser exception.

## Data Flow Pipeline

```
1. [CLI Invocation]
   |
   v
2. [Manifest Parser] --(package names + versions)--> [OSV Mapper]
   |                                                |
   |--(source file list)---------------------------> [AST Builder]
   |                                                |
   |--(package paths)------------------------------> [site-packages Resolver]
                                                      |
   v                                                  v
3. [AST Builder] --(AST + symbol tables)----------> [Call Graph Engine]
   [site-packages Resolver] --(lib code paths)-----> [Call Graph Engine]
                                                      |
                                                      v
4. [Call Graph Engine] --(DiGraph)----------------> [Reachability Analyzer]
   [OSV Mapper] --(vulnerable symbols)-------------> [Reachability Analyzer]
                                                      |
                                                      v
5. [Reachability Analyzer] --(classified results)-> [SARIF Serializer]
                                                      |
                                                      v
6. [SARIF Serializer] --(sarif.json)--------------> [Filesystem / CI Artifact]
   [CLI Reporter] --(stdout summary)---------------> [User / CI Log]
```

## Deployment Architecture

### Local Developer Mode
```
Developer Workstation
├── PyReach CLI (Poetry venv)
├── Local OSV SQLite DB (~/.pyreach/osv.db)
└── Target Python Project
    ├── src/
    ├── requirements.txt
    └── .pyreach.yml (config)
```

### CI/CD Runner Mode (GitLab / Jenkins)
```
Corporate CI Runner (Lidercom On-Prem)
├── PyReach installed via pip / Poetry
├── Pre-seeded OSV SQLite DB (updated weekly via cron)
└── Build Pipeline Stage
    ├── Unit Tests
    ├── PyReach Security Scan (SARIF artifact)
    └── Quality Gate (exit code check + SARIF dashboard ingest)
```

## Technology Stack

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| Language | Python | >=3.10 | Native `ast` module improvements, pattern matching, type hints |
| Dependency Mgmt | Poetry | >=1.7 | Reproducible builds, lock file, virtual env management |
| Graph Library | NetworkX | >=3.0 | Mature DiGraph, optimized traversal, serialization |
| Database | SQLite | >=3.39 (stdlib) | Zero-config, local file, sufficient for advisory dataset |
| Testing | pytest | >=7.0 | TDD fixtures, parametrization, coverage plugins |
| Validation | jsonschema | >=4.0 | SARIF schema conformance verification in tests |
| CLI Framework | argparse (stdlib) | - | No extra dependency; sufficient for current scope |

## Security & Performance Considerations

- **Memory**: For large transitive dependency trees, NetworkX DiGraph may consume significant RAM. Mitigation: limit graph to application + direct dependencies first; lazily load transitive library ASTs only when vulnerable symbols are present.
- **Recursion Depth**: Python's default recursion limit (~1000) may be exceeded in deep call chains. Use iterative BFS/DFS for graph traversal.
- **Injection Safety**: When parsing manifests, never `eval()` requirements lines. Use regex-based or `packaging.requirements` parser.
- **Path Traversal**: Ensure all file reads are confined to the target project directory and resolved `site-packages` paths. Reject relative paths containing `..`.

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
