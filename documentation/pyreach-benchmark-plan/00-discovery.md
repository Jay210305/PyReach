# 00 — Discovery and gate G0

## Problem and goal
Dependency scanners identify vulnerable packages but often lack evidence that an application entry point can reach the vulnerable function. Establish independently auditable estimates of PyReach call-graph quality, vulnerability reachability, offline behavior, CLI correctness and real-project performance.

## Proposed measurable success criteria (ASSUMPTION; targets, **not measured facts**)
| ID | Target | Evidence | Role |
|---|---|---|---|
| M1 | Attempt all **233 unique** PyAnalyzer micro-tests (206 original PyCG + 27 new), publish N scored / unsupported / errors | complete case ledger; no fabricated edges | Must |
| M2 | Attempt all **5** manual-curated PyAnalyzer/PyCG macro graphs; score supported graphs | edge precision/recall/F1 + exclusions | Must |
| M3 | Attempt FASTEN 5-package micro and Fabric macro; report unresolved cross-package edges explicitly | graph/path comparison | Must |
| M4 | Review SWARM-CG Python fixtures, and report subset coverage with explicit eligibility | eligibility record | Must |
| M5 | Build **36 controlled** cases: 12 reachable, 12 unreachable, 12 unknown; zero unreviewed labels | fixture manifest and review checks | Must |
| M6 | Attempt **4** project cohorts: VulnReach lab + PyGoat, Django RealWorld + FastAPI template, Saleor + Wagtail (6 repo paths total, more than minimum) | 6 pin records, scan outcomes or documented blockers | Must |
| M7 | 100% of produced SARIF runs validate v2.1.0; 100% expected CLI exit codes in controlled checks; blocked/errors separately reported | automated suite | Must |
| M8 | Zero network calls **during analysis** under isolated execution; setup is allowed online | isolation log and run record | Must |
| M9 | ≥3 repeats per eligible real project, and log median/p95 wall time + peak RSS, no invented <45s guarantee | measured runs on specified host | Must |
| M10 | Source report with exact revisions, fixture/schema/DB hashes, denominator accounting, reproducible commands | evidence manifest | Must |

**Not a hard performance pass gate:** `<45s` from example methodology is illustrative, not a user-confirmed PyReach requirement. Report measured runtime; choose limits after baseline.

## Stakeholders and team
- **Decision maker:** PyReach owner / user; approval pending.
- **Executor and single sprint owner:** `benchmark-agent` (ASSUMPTION: one agent, 13 productive h/week for 10 weeks).
- **Optional reviewer:** user; no guaranteed advisory availability. No automatic public release authorization.
- **Platform ASSUMPTION:** Debian under WSL2, `uv`, Git, local SQLite OSV DB, Python toolchain; hardware limits and DB contents to be verified.

## Scope
- Adapt graph ground truth rather than assume PyReach exposes `--dump-callgraph`.
- Deterministic offline fixture tests, vulnerability-symbol provenance and unknown-case semantics.
- Independent macro/micro graph testing and selected real project scans.
- Baseline distinctions (`pip-audit`, OSV-Scanner package detection; PyCG/Pyan3 call graphs; VulnReach reachability if runnable).
- JSON/SARIF artifact checks, CLI/CI exit codes, time/memory, failure categorization, reproducibility/reporting.

## Explicit out-of-scope
- Rebuild PyReach or change its externally documented CLI without separate ADR/approval.
- Exploit development or execution of untrusted vulnerable applications; no intentional malicious payloads.
- Publishing full third-party source archives, redistributing proprietary Safety feeds, or claiming public CI is safe for untrusted code.
- Exploitability claims based solely on static reachability; static analysis ≠ runtime exploit proof.
- GitHub activity monitoring or broad unrelated language ecosystems.
- Running every Vul4Py case unless package/symbol mapping is available and permitted.

## Assumptions, external dependencies, and reality checks
`ASSUMPTION A1` PyReach repo and OSV DB will be available locally when the agent begins. `ASSUMPTION A2` 13 h/week capacity and a five-sprint (10-week) envelope, not a deadline. `ASSUMPTION A3` offline scans are isolated after an explicitly online data-acquisition stage. `ASSUMPTION A4` the agent can add a benchmark harness inside PyReach. `ASSUMPTION A5` frozen network/download timestamps + licenses can be recorded. `ASSUMPTION A6` some graph comparisons will be `unsupported` unless an internal graph projection can be implemented without affecting production behavior.

**External dependencies:** GitHub source availability, UV cache, benchmark licenses, externally downloaded SARIF schema, SQLite DB snapshot. For each, use controlled source lock and checksums. Any unavailable corpus is `blocked`, never automatically `passed` or silently omitted.

## Glossary
**SCA** package/version vulnerability matching. **Reachable** statically supported entry-to-symbol call path. **Unreachable** graph-grounded absence under supported closed-world fixtures only. **Unknown** incomplete symbol, edges, entrypoints, dynamic dispatch or advisory provenance. **Ground truth** manually curated/reference annotations; **baseline** comparator tool; **coverage** proportion eligible/analyzed (distinct from code coverage). **Case** one pinned test evaluation unit. **Blocked/unsupported** no reliable score due to external resource/feature mismatch.

## Discovery approval checklist — gate G0 (PENDING)
- [ ] User approves goal, 10 quantitative targets and explicit out-of-scope.
- [ ] User accepts or updates 13h/week, ten-week plan, capacity and target platform.
- [ ] Verify PyReach repository, CLI, graph projection options, OSV DB schema and licensing permissions with audit; publish delta ADR if assumptions differ.

**Agent stop rule:** you may inspect sources and produce spike evidence without user approval; do not mark downstream `Ready` or claim benchmarks completed before G0 is approved. If proceeding on explicit agent delegation, log owner acceptance in `tracking/approval-gates.md`.
