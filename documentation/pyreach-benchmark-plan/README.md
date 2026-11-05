# PyReach — reproducible benchmark and field-validation program

**Status:** Planning package v0.1.0 (DRAFT; not execution-approved)  
**Prepared:** 2026-10-13  
**Audience:** autonomous coding agent working in the existing PyReach repository  
**Planning basis:** `planning-methodology-original.md` (user-provided)

## Mission
Evaluate PyReach, a local-first Python dependency vulnerability reachability scanner, on independent call-graph ground truth, controlled advisory/symbol fixtures, and pinned real Python projects. Produce quantitative, reproducible evidence instead of merely counting vulnerabilities.

## Agent: read and execute in this order
1. Read `00-discovery.md`, `01-overview.md`, `03-technical-spec.md`, `docs/contracts/README.md` and `tracking/approval-gates.md` **before coding**.
2. Obtain or record user approval for discovery scope/success criteria (Gate G0). All provisional targets are `ASSUMPTION`; **do not claim they were approved**.
3. Audit the PyReach repo with `S0-T1`; resolve repository/API/OSV schema unknowns and record an ADR before adapting contracts. Do not fabricate graph export, DB schema, vulnerable-symbol mapping, or source commit hashes.
4. Follow `04-implementation-roadmap.md`, then execute each task from `implementation/README.md` in dependency order. **Each task is self-contained** and references its immutable contract. Check the Definition of Ready before starting.
5. Run `python3 scripts/validate_plan.py` now and after every planning edit. Sprint quality gates are centralized in `06-ci-cd-environments.md`.
6. Track actual effort and blockers in `tracking/progress-log.md`, debt in `tracking/debt-backlog.md`; preserve results + hashes. Release only after the explicit close-out gate.

## Immediate bootstrap
```bash
python3 scripts/validate_plan.py
# Run these only after a user-approved target directory, sufficient disk space, and a committed PyReach checkout:
# uv sync
# uv run --offline --no-sync pyreach /path/to/project --db-path ~/.pyreach/osv.db -o result.sarif
```

## What's in this package
- `00` through `10`: discovery, constraints/spec, architecture, testing, CI, risks, quantitative KPIs, ADR process, research source catalog.
- `docs/contracts/`: versioned CLI, benchmark case, source-lock, graph, vulnerability-symbol, result and report contracts.
- `implementation/`: **22 task cards**, a roadmap-linked index, dependencies, ≤2-hour test-first subtasks, verification.
- `traceability.md`: Requirements → tasks → tests; `tracking/`: pending approvals, progress/debt.
- `scripts/validate_plan.py`: offline plan lint (hours, IDs, dependencies, links, subtask limits).

## Critical caveats
- The PyReach repository itself and its OSV SQLite schema were **not supplied**. Commands and adapter paths beyond the public CLI are target artifacts, not claims about existing code.
- The existing PyCG 206 cases are a subset of PyAnalyzer's 233. Count **233 unique** micro-cases, not 439.
- OSV package/version matching does **not** generally prove a vulnerable symbol. Any unsupported symbol mapping is **indeterminate** and remains visible.
- The Safety dataset's commercial-scale data is **not publicly redistributable**; inspect public samples and license limits first.
- Vul4Py targets automated vulnerability **repair**, not package-to-symbol reachability. Only admissible cross-mapped cases can be scored for PyReach.
- Benchmarks are planned, **not executed**. There are no claimed PyReach scores in this ZIP.

## Required local layout after implementation (inside PyReach repository)
`benchmarks/pyreach_eval/` (source, data adapters, tests, reporting), `benchmarks/reports/` (generated, gitignored except small representative summaries). Third-party repositories, OSV DB dumps and licensed datasets stay outside version control.
