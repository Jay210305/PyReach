# Implementation Roadmap

## Phase 2 Development Plan (Weeks 5-12)

Phase 2 is organized into **4 biweekly sprints** totaling 240 person-hours. Each sprint has defined deliverables, acceptance criteria, estimated effort, and risk mitigations aligned with the project constraints (TIME is non-negotiable, COST is capped, SCOPE is negotiable).

---

## Sprint 1: Dependency Parser, OSV Ingestion, and TDD Fixtures
**Duration**: Weeks 5-6  
**Effort**: 40 hours (Julio Centeno)  
**Goal**: Establish the data ingestion pipeline and testing foundation.

### Deliverables
1. `pyreach.parsers.manifest` module with `requirements.txt` and `Pipfile.lock` support.
2. `pyreach.osv.importer` module for bulk OSV JSON -> SQLite ingestion.
3. `pyreach.db.schema.sql` DDL and `pyreach.db.connection` context manager.
4. pytest fixture suite with 80%+ coverage for parser and importer modules.
5. Initial CI pipeline configuration (GitLab `.gitlab-ci.yml` or Jenkinsfile) running tests on every commit.

### Detailed Tasks

| Task ID | Description | Effort (hrs) | Owner | Acceptance Criteria |
|---------|-------------|--------------|-------|---------------------|
| S1-T1 | Design `Dependency` dataclass and parser interface | 4 | Julio | Interface reviewed by Alonso; documented in docstrings |
| S1-T2 | Implement `requirements.txt` regex/line parser | 8 | Julio | Passes 20 unit test cases including extras, markers, editable installs |
| S1-T3 | Implement `Pipfile.lock` JSON parser | 6 | Julio | Passes 10 unit test cases; falls back gracefully if file missing |
| S1-T4 | Design SQLite schema (advisories, affected_symbols, cg_nodes, cg_edges, reachability_results) | 4 | Julio | Schema reviewed; 3NF compliance check |
| S1-T5 | Implement `OSVImporter` with JSONL streaming | 10 | Julio | Successfully ingests 10,000+ OSV PyPI records in <5 min |
| S1-T6 | Write pytest fixtures and parametrized tests for parsers | 6 | Julio | >=80% branch coverage on parsers; all tests green |
| S1-T7 | Set up GitLab CI runner stage for pytest | 2 | Julio | Pipeline runs on push; failure blocks merge |

### Definition of Done
- All S1 tasks complete and merged to `main`.
- `pytest --cov` reports >=80% coverage on `parsers/` and `osv/`.
- OSV SQLite DB can be generated from raw OSV JSONL dump via single command.
- No critical or high bugs in SonarQube / ruff linting.

### Risk Mitigations
- **R7 (AST complexity slippage)**: Not applicable yet; buffer reserved for Sprint 2.
- **R6 (Academic overload)**: Sprint 1 scheduled before midterm week 8.

---

## Sprint 2: AST Syntactic Engine and Alias Resolution
**Duration**: Weeks 7-8  
**Effort**: 45 hours (Julio Centeno)  
**Goal**: Build the static analysis foundation for code comprehension.

### Deliverables
1. `pyreach.ast.builder` module: parse `.py` files into `ModuleAST` objects.
2. `pyreach.ast.symbols` module: per-module symbol table construction.
3. `pyreach.ast.resolver` module: import alias resolution across application and site-packages.
4. `pyreach.loaders.source` and `pyreach.loaders.packages` modules.
5. Comprehensive test suite for AST traversal, symbol tables, and import resolution.

### Detailed Tasks

| Task ID | Description | Effort (hrs) | Owner | Acceptance Criteria |
|---------|-------------|--------------|-------|---------------------|
| S2-T1 | Mitigation M1: Intensive self-study on `ast` module internals (2 days) | 16 | Julio | Can manually traverse and classify all node types in sample files |
| S2-T2 | Implement `SourceLoader` with ignore pattern support | 4 | Julio | Discovers all `.py` files excluding `venv/`, `__pycache__/` |
| S2-T3 | Implement `PackageResolver` mapping package names to site-packages paths | 6 | Julio | Resolves 100% of installed packages in a test venv |
| S2-T4 | Implement `ASTBuilder`: parse files, compute module FQN, wrap in `ModuleAST` | 8 | Julio | Parses 50 diverse Python files without syntax errors; skips invalid files with warning |
| S2-T5 | Implement `SymbolTableBuilder`: map local names, imports, `from...import` | 10 | Julio | Correctly resolves `import numpy as np`, `from x import y as z`, `from . import sibling` |
| S2-T6 | Implement `ImportResolver`: cross-module alias to fully qualified names | 8 | Julio | Given `import requests`, resolves `requests.get` to `requests.api.get` |
| S2-T7 | Write pytest fixtures with real-world code samples (requests, flask snippets) | 6 | Julio | >=80% coverage on `ast/` and `loaders/` modules |

### Definition of Done
- `ASTBuilder` and `SymbolTableBuilder` pass all tests on real-world library code (requests, Flask, FastAPI stubs).
- Import resolution works for absolute imports, relative imports (intra-package), and star imports (`from module import *`).
- `PackageResolver` correctly maps all packages in a Poetry virtual environment.
- Coverage >=80% on new code.

### Risk Mitigations
- **R7 (AST complexity)**: Mitigation M1 (self-study) front-loaded in S2-T1. If slippage >15%, scope trimmed: deprioritize `Pipfile.lock` support or complex `__init__.py` namespace packages.
- **R2 (Dynamic constructs)**: Not handled yet; deferred to Sprint 3 heuristic design.

---

## Sprint 3: Call Graph Construction (NetworkX) and Reachability Algorithm
**Duration**: Weeks 9-10  
**Effort**: 45 hours (Jose Alonso Yanez)  
**Goal**: Construct the interprocedural call graph and implement bounded reachability analysis.

### Deliverables
1. `pyreach.callgraph.engine` module: NetworkX DiGraph construction from ASTs.
2. `pyreach.callgraph.nodes` and `pyreach.callgraph.edges` modules.
3. `pyreach.reachability.analyzer` module: bounded BFS/DFS traversal.
4. `pyreach.reachability.classifier` module: result classification logic.
5. `pyreach.reachability.entrypoints` module: entry point detection and configuration.
6. Integration tests verifying end-to-end reachability on synthetic vulnerable projects.

### Detailed Tasks

| Task ID | Description | Effort (hrs) | Owner | Acceptance Criteria |
|---------|-------------|--------------|-------|---------------------|
| S3-T1 | Mitigation M3: Study NetworkX DiGraph APIs and PyCG paper algorithms | 8 | Alonso | Can build, traverse, and serialize DiGraphs; understands PyCG node/edge types |
| S3-T2 | Design `CGNode` and `CGEdge` dataclasses with type annotations | 4 | Alonso | Reviewed by Julio; documented; immutable/frozen |
| S3-T3 | Implement node extraction: functions, methods, lambdas, classes | 10 | Alonso | Extracts >=95% of callable nodes in standard Python code |
| S3-T4 | Implement edge extraction: static calls, inheritance, imports | 12 | Alonso | Correctly links `caller()` -> `callee()` for direct and method calls |
| S3-T5 | Implement bounded reachability BFS (max depth k=5) with memoization | 12 | Alonso | Completes on 100-node graph in <100ms; handles cycles gracefully |
| S3-T6 | Implement classifier: REACHABLE / NOT_REACHABLE / POTENTIALLY_REACHABLE | 6 | Alonso | Unit tests for all three categories; 0 false negatives on test suite |
| S3-T7 | Implement entry point auto-detection (`__main__`, CLI-configured) | 4 | Alonso | Detects `if __name__ == "__main__"` and respects `-e` overrides |
| S3-T8 | Integration test: synthetic project with known reachable/unreachable CVEs | 6 | Alonso | Passes 5 synthetic scenarios with 100% accuracy |

### Definition of Done
- Call graph builds correctly for a medium-sized project (e.g., Flask app with 10 deps) in <10 seconds.
- Reachability analyzer classifies all synthetic test CVEs correctly.
- POTENTIALLY_REACHABLE heuristic implemented for `eval`, `exec`, `getattr`, `importlib` patterns.
- Coverage >=80% on `callgraph/` and `reachability/`.

### Risk Mitigations
- **R1 (Combinatorial explosion)**: Limit max depth to k=5. Use NetworkX `DiGraph` (not `MultiDiGraph`) to collapse parallel edges. Monitor memory with `tracemalloc` in tests.
- **R2 (Dynamic metaprogramming)**: Preventive heuristic: any call chain traversing a `DYNAMIC` edge or unresolved import defaults to POTENTIALLY_REACHABLE.

---

## Sprint 4: SARIF Serializer, CLI, and CI/CD Quality Gates
**Duration**: Weeks 11-12  
**Effort**: 42 hours (Jose Alonso Yanez)  
**Goal**: Deliver the user-facing tool with standardized output and pipeline integration.

### Deliverables
1. `pyreach.output.sarif` module: validated SARIF v2.1.0 serialization.
2. `pyreach.cli` module: complete CLI with all specified options and exit codes.
3. `pyreach.config` module: `.pyreach.yml` loader and validation.
4. CI/CD integration scripts and documentation.
5. Local runner deployment package for Lidercom's server.
6. CLI user manual (Markdown).

### Detailed Tasks

| Task ID | Description | Effort (hrs) | Owner | Acceptance Criteria |
|---------|-------------|--------------|-------|---------------------|
| S4-T1 | Design SARIF builder classes mapping PyReach results to OASIS schema | 6 | Alonso | Class diagram reviewed by Julio |
| S4-T2 | Implement SARIF serialization with `codeFlows` for reachable paths | 10 | Alonso | Output validates against jsonschema SARIF v2.1.0 schema in tests |
| S4-T3 | Implement CLI argument parsing, config loading, and execution orchestration | 8 | Alonso | All options from technical spec work; `--help` is comprehensive |
| S4-T4 | Implement exit code logic and error handling hierarchy | 4 | Alonso | Exit codes 0/1/2 behave as specified; integration tests verify |
| S4-T5 | Implement `.pyreach.yml` parser and merge with CLI overrides | 4 | Alonso | Config file values correctly overridden by CLI flags |
| S4-T6 | Build CI/CD stage templates (GitLab CI job, Jenkins stage) | 6 | Alonso | Example `.gitlab-ci.yml` snippet runs pyreach and gates on exit code |
| S4-T7 | Deploy to Lidercom local runner and validate performance (<45s) | 6 | Alonso | Scans Lidercom's largest microservice in <45 seconds |
| S4-T8 | Write CLI user manual and architecture overview doc | 4 | Joint | Approved by Dr. Torres and Lidercom key users |

### Definition of Done
- CLI is installable via `pip install .` or `poetry install` and runs on Python 3.10+ without extra dependencies beyond those in `pyproject.toml`.
- SARIF output is accepted by GitLab CI security dashboard (tested on Lidercom runner).
- Scan completes in <45s on target microservice.
- All integration tests pass; coverage >=80% overall.
- Documentation complete and reviewed.

### Risk Mitigations
- **R3 (SARIF schema rejection)**: Automated jsonschema validation in TDD tests from day one of Sprint 4.
- **R4 (Lidercom access delay)**: Containerized Docker replica of a generic Python microservice maintained as contingency test target.

---

## Sprint Dependencies & Critical Path

```
Sprint 1 (Parser/OSV) ----+
                          +--> Sprint 3 (Call Graph/Reachability) --> Sprint 4 (SARIF/CLI)
Sprint 2 (AST Engine) ----+
```

**Critical Path**: S1 -> S3 -> S4 (total 10 weeks).  
**Float**: S2 has some flexibility but must complete before S3 starts.

## Milestones & Checkpoints

| Milestone | Date (Week) | Criteria |
|-----------|-------------|----------|
| M1: Data Foundation | End of Week 6 | OSV DB ingestible; manifests parseable; CI green |
| M2: Code Comprehension | End of Week 8 | AST engine resolves imports and symbols on real code |
| M3: Analysis Core | End of Week 10 | Call graph + reachability yields correct classifications on synthetic projects |
| M4: Product Delivery | End of Week 12 | CLI installable; SARIF valid; CI gate functional; <45s scan |

## Buffer & Contingency

- **Schedule buffer**: 3 days per sprint (approx 15% of biweekly capacity) reserved for rework, bug fixes, and advisor review.
- **Scope negotiation triggers**:
  - If Sprint 1 slips >3 days: Drop `Pipfile.lock` support; focus only on `requirements.txt`.
  - If Sprint 2 slips >3 days: Reduce import resolution complexity; skip star-import resolution (`from x import *`).
  - If Sprint 3 slips >3 days: Reduce max depth default from 5 to 3; postpone memoization optimization.
  - If Sprint 4 slips >3 days: Postpone `.pyreach.yml` config file; rely on CLI flags only.

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
