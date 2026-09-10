# PyReach — Detailed Implementation Task Breakdown

This folder expands every task from [`../04-implementation-roadmap.md`](../04-implementation-roadmap.md)
into **essential, independently executable sub-tasks**. Each file is a self-contained work
package that a developer can pick up without reading the whole roadmap.

## Source of Truth

The roadmap (`04-implementation-roadmap.md`) defines **what** must be delivered per sprint.
This folder defines **how** each task is decomposed and **what "done" looks like** at the
sub-task level. Where these documents disagree, the roadmap's acceptance criteria win, and
this folder should be corrected.

## Folder Layout

```
implementation/
├── README.md                          <- this index + conventions
├── sprint-1-data-foundation/          <- Parser, OSV ingestion, TDD fixtures (Weeks 5-6)
├── sprint-2-ast-engine/               <- AST engine + alias resolution (Weeks 7-8)
├── sprint-3-callgraph-reachability/   <- Call graph + reachability (Weeks 9-10)
└── sprint-4-sarif-cli/                <- SARIF, CLI, CI/CD gates (Weeks 11-12)
```

Each sprint folder contains one Markdown file per roadmap task, named
`sprint-task-<slug>.md`, e.g. `S1-T2-requirements-txt-parser.md`.

## File Format

Every task file uses the same structure:

| Section | Meaning |
|---------|---------|
| Metadata | Task ID, sprint, owner, effort, dependencies, related docs |
| Purpose | Why the task exists and what problem it solves |
| Preconditions | What must be true before starting |
| Essential Sub-tasks | Numbered, atomic units of work with step-by-step instructions |
| Deliverables | Concrete files/artifacts produced |
| Acceptance Criteria | Verifiable pass/fail conditions from the roadmap |
| Verification | Exact commands/tests to run |
| Edge Cases & Pitfalls | Known traps and how to handle them |
| Risks / Scope Cuts | Link to risk register items and fallback plan |
| Definition of Done | Checklist to close the task |

## Conventions Used

- **Effort** is quoted in hours from the roadmap. Sub-task hours should sum to the task total.
- **File paths** follow the package structure in
  [`../03-technical-specifications.md`](../03-technical-specifications.md) §2.
- **Data contracts** (`Dependency`, `ModuleAST`, `CGNode`, `CGEdge`, `Vulnerability`,
  `ReachabilityResult`) are defined in `03-technical-specifications.md` §3.
- **TDD is mandatory**: each implementation sub-task is preceded by its failing test.
- **No comments in code** unless a non-obvious algorithm requires one; rely on docstrings.
- Coverage gate: `>=80%` overall, higher on critical modules (see `08-testing-strategy.md` §7).

## Task Index

### Sprint 1 — Data Foundation (40 h, Julio Centeno)

| Task | File | Roadmap |
|------|------|---------|
| S1-T1 | [Design Dependency dataclass and parser interface](sprint-1-data-foundation/S1-T1-dependency-dataclass-and-parser-interface.md) | S1-T1 |
| S1-T2 | [Implement requirements.txt parser](sprint-1-data-foundation/S1-T2-requirements-txt-parser.md) | S1-T2 |
| S1-T3 | [Implement Pipfile.lock parser](sprint-1-data-foundation/S1-T3-pipfile-lock-parser.md) | S1-T3 |
| S1-T4 | [Design SQLite schema](sprint-1-data-foundation/S1-T4-sqlite-schema-design.md) | S1-T4 |
| S1-T5 | [Implement OSVImporter](sprint-1-data-foundation/S1-T5-osv-importer.md) | S1-T5 |
| S1-T6 | [pytest fixtures and parser tests](sprint-1-data-foundation/S1-T6-pytest-fixtures-parsers.md) | S1-T6 |
| S1-T7 | [GitLab CI pytest stage](sprint-1-data-foundation/S1-T7-gitlab-ci-pytest-stage.md) | S1-T7 |

### Sprint 2 — AST Engine (45 h, Julio Centeno)

| Task | File | Roadmap |
|------|------|---------|
| S2-T1 | [AST module self-study (Mitigation M1)](sprint-2-ast-engine/S2-T1-ast-module-self-study.md) | S2-T1 |
| S2-T2 | [Implement SourceLoader](sprint-2-ast-engine/S2-T2-source-loader.md) | S2-T2 |
| S2-T3 | [Implement PackageResolver](sprint-2-ast-engine/S2-T3-package-resolver.md) | S2-T3 |
| S2-T4 | [Implement ASTBuilder](sprint-2-ast-engine/S2-T4-ast-builder.md) | S2-T4 |
| S2-T5 | [Implement SymbolTableBuilder](sprint-2-ast-engine/S2-T5-symbol-table-builder.md) | S2-T5 |
| S2-T6 | [Implement ImportResolver](sprint-2-ast-engine/S2-T6-import-resolver.md) | S2-T6 |
| S2-T7 | [AST pytest fixtures with real-world samples](sprint-2-ast-engine/S2-T7-ast-pytest-fixtures.md) | S2-T7 |

### Sprint 3 — Call Graph & Reachability (45 h, Jose Alonso Yanez)

| Task | File | Roadmap |
|------|------|---------|
| S3-T1 | [NetworkX + PyCG study (Mitigation M3)](sprint-3-callgraph-reachability/S3-T1-networkx-and-pycg-study.md) | S3-T1 |
| S3-T2 | [Design CGNode and CGEdge](sprint-3-callgraph-reachability/S3-T2-cgnode-cgedge-design.md) | S3-T2 |
| S3-T3 | [Implement node extraction](sprint-3-callgraph-reachability/S3-T3-node-extraction.md) | S3-T3 |
| S3-T4 | [Implement edge extraction](sprint-3-callgraph-reachability/S3-T4-edge-extraction.md) | S3-T4 |
| S3-T5 | [Implement bounded reachability BFS](sprint-3-callgraph-reachability/S3-T5-bounded-reachability-bfs.md) | S3-T5 |
| S3-T6 | [Implement classifier](sprint-3-callgraph-reachability/S3-T6-classifier.md) | S3-T6 |
| S3-T7 | [Implement entry point detection](sprint-3-callgraph-reachability/S3-T7-entry-point-detection.md) | S3-T7 |
| S3-T8 | [Synthetic integration test](sprint-3-callgraph-reachability/S3-T8-synthetic-integration-test.md) | S3-T8 |

### Sprint 4 — SARIF, CLI & CI/CD (42 h, Jose Alonso Yanez)

| Task | File | Roadmap |
|------|------|---------|
| S4-T1 | [Design SARIF builder classes](sprint-4-sarif-cli/S4-T1-sarif-builder-design.md) | S4-T1 |
| S4-T2 | [Implement SARIF serialization with codeFlows](sprint-4-sarif-cli/S4-T2-sarif-serialization.md) | S4-T2 |
| S4-T3 | [Implement CLI orchestration](sprint-4-sarif-cli/S4-T3-cli-orchestration.md) | S4-T3 |
| S4-T4 | [Implement exit codes and error hierarchy](sprint-4-sarif-cli/S4-T4-exit-codes-and-errors.md) | S4-T4 |
| S4-T5 | [Implement .pyreach.yml config](sprint-4-sarif-cli/S4-T5-pyreach-yml-config.md) | S4-T5 |
| S4-T6 | [Build CI/CD stage templates](sprint-4-sarif-cli/S4-T6-cicd-stage-templates.md) | S4-T6 |
| S4-T7 | [Deploy to Lidercom runner and benchmark](sprint-4-sarif-cli/S4-T7-lidercom-deploy-benchmark.md) | S4-T7 |
| S4-T8 | [Write CLI manual and architecture doc](sprint-4-sarif-cli/S4-T8-cli-manual-and-architecture-doc.md) | S4-T8 |

## Critical Path

```
Sprint 1 (S1-T1 -> S1-T2 -> S1-T4 -> S1-T5) ---+
                                               +--> Sprint 3 (S3-T2 -> S3-T3 -> S3-T4 -> S3-T5) --> Sprint 4 (S4-T1 -> S4-T2 -> S4-T3)
Sprint 2 (S2-T1 -> S2-T4 -> S2-T5 -> S2-T6) ---+
```

The critical path is **S1 -> S3 -> S4**. Sprint 2 must finish before Sprint 3 starts.
Within a sprint, tasks listed later normally depend on earlier ones.

## Cross-Cutting Rules

1. **TDD**: write the failing test first; reference the test name in the sub-task.
2. **Atomic commits**: one task (or sub-task group) per commit, referencing the task ID.
3. **Type hints**: all public functions annotated; `mypy` clean.
4. **Lint**: `ruff` clean before merge.
5. **No network at analysis time**: only `sync-osv` may touch the network.
6. **Determinism**: tests must not depend on the full OSV dump or external services.

## Document Control

- Derived from `04-implementation-roadmap.md` v1.0 (2026-09-10).
- Version: 1.0
- Maintainers: Julio Centeno, Jose Alonso Yanez.
