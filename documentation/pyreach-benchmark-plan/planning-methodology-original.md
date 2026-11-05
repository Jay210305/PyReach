# Project Planning Methodology (spec → roadmap → implementation)

> **Instruction to the agent:** follow this document IN ORDER to plan a project.
> Do not move to the next step until the **Gate** of the current one is met. Do not invent data:
> if information is missing (constraints, timelines, team), ask the user or mark it as an
> `ASSUMPTION` in the document. Every plan must be executable without having to read any file
> other than the one currently being worked on.

---

## 1. Principle: 3 layers

```
spec docs (01-10)  →  roadmap (04)  →  implementation/SX-TY-*.md
   WHAT it is          WHAT / WHEN / WHO          HOW + DONE
```

| Layer | Content | Question it answers |
|---|---|---|
| **Spec (01-10)** | Overview, architecture, technical spec (data contracts, API/CLI), testing, CI/CD, risks, metrics | What is it and how is it built? Without this you cannot estimate |
| **Roadmap (04)** | Phases split into timeboxed 2-week sprints with a **single owner per sprint** | What is delivered, when, and by whom? |
| **Implementation** | 1 executable file per task (`SN-TM-slug.md`) | How is it done and when is it finished? |

**Golden rule:** each layer derives from the previous one. If a task does not trace back to a spec
requirement, it is surplus; if a requirement has no task, something is missing.

---

## 2. Recipe

### Step 0 — Discovery *(added)*
Before anything else, write `00-discovery.md` with:
- **Problem and goal** in 1–2 sentences; **measurable success criteria** (e.g. "<45 s per analysis").
- **Stakeholders and team**: who decides, who executes, availability (h/week per person).
- **Scope / Out of scope**: an explicit list of what will NOT be done.
- **Assumptions** and **external dependencies** (APIs, data, permissions, hardware, third parties).
- **Glossary** of domain terms.

**Gate:** the user approves the goal, success criteria, and out-of-scope list.

### Step 1 — Fix the constraints
State which are:
- **Non-negotiable** (deadline, regulatory or performance requirement).
- **Capped** (budget, total hours, infrastructure).
- **Negotiable** (scope, nice-to-haves).

Example (PyReach): `<45 s`, local-first, valid SARIF.
Also classify each requirement with **MoSCoW** (Must / Should / Could / Won't) *(added)*.

**Gate:** every requirement has a MoSCoW priority; the Musts fit in the available time.

### Step 2 — Write the spec (docs 01-10) *(expanded)*
Recommended minimum (adapt to the project type):

| # | Document | Notes |
|---|---|---|
| 01 | Overview | Vision, users, use cases |
| 02 | Architecture | Diagram, components, data flow, **repo structure and dependency rules** *(see below)* |
| 03 | Technical spec | Data contracts, schemas, API/CLI (detail in Step 5) |
| 04 | Implementation roadmap | See Step 3 |
| 05 | Testing | Strategy, pyramid, test data/fixtures, coverage thresholds |
| 06 | CI/CD and environments | Pipeline, **single quality-gates table**, versioning, branching strategy |
| 07 | Risks | R1…Rn with owner and mitigation |
| 08 | Metrics / NFRs | Performance, security, accessibility, observability |
| 09 | Decisions (ADRs) | One architecture decision per entry: context, options, decision, consequences |
| 10 | Glossary and references | Optional if already covered in 00 |

**Repo structure and dependency rules *(added)*:** in `02`, include the directory tree, which
module belongs to whom, and which layer may import which (e.g. `domain` must not import
`infra`). Where possible, make it automatically verifiable (import-linter, dependency-cruiser,
etc.).

**Uniform quality gates *(added)*:** a single table (lint, types, tests, minimum coverage,
security scan) that runs identically locally and in CI; DoDs and tasks reference it instead of
repeating it.

**Spikes *(added)*:** any technical uncertainty that prevents estimating (unfamiliar library,
doubtful performance, external integration) is resolved with a **timeboxed spike (≤4 h)** before
Step 4. Output: a decision (ADR) and an adjusted estimate.

**Traceability *(added)*:** keep a `Requirement → Task → Test` table to verify full scope coverage.

**Gate:** the spec is sufficient to estimate; there is no "TBD" in data contracts or in Must NFRs;
spikes are resolved.

### Step 3 — Define sprints in the roadmap
Timeboxed 2-week sprints, **one single owner per sprint**. Use this block verbatim:

```markdown
## Sprint N: <name> (weeks X-Y)
**Duration:** … | **Effort:** … h | **Status:** ⬜ | **Owner:** …
**Goal:** <1 sentence>

### Deliverables
1. <module/file>
2. …

| ID | Description | Effort (h) | Assignee | Status | Acceptance criteria |
|----|-------------|------------|----------|--------|---------------------|
| SN-T1 | … | 8 | … | ⬜ | measurable: "10k records <5 min", "100 nodes <100 ms" |

### DoD
- [ ] Coverage ≥ X %
- [ ] Build/CI green
- [ ] Documentation updated

### Mitigations
- R1 → concrete task (SN-Tx)
```

Rules:
- Acceptance criteria are **always measurable** (number, threshold, pass/fail).
- **Walking skeleton first *(added)*:** the first sprint delivers a thin end-to-end vertical slice
  (even if trivial) with green CI, before deepening each module. Plan by **vertical slices**
  (complete functional value), not by technical layers.
- **Size limits *(added)*:** task ≤ 8 h and sub-task ≤ 2 h; if exceeded, split. Each task must end
  in something **mergeable and independently verifiable**.
- **Definition of Ready *(added)*:** a task does not enter the sprint without resolved
  dependencies, a defined interface contract (Step 5), clear criteria, and an estimate.
- Add a **Sprint 0 *(added)*** if needed: repo, CI, environment, sample data.
- Reserve a **stabilization sprint/window *(added)*** at the end: bugs, docs, demo.

**Gate:** all Must tasks are assigned to a sprint, have a measurable criterion, and respect the
size limits.

### Step 4 — Estimate by sum + slack
```
Σ sprint effort  +  slack (buffer ≈15 % + docs + validation + advisor meetings)  =  total
```
PyReach example: 44+45+45+42 = 176 h + 64 h (32 buffer + 12 docs + 8 validation + 12 advisory) = 240 h.

- Record the **reconciliation in a table** (hours per sprint, buffer, total vs. real capacity).
- **Check capacity *(added)*:** total hours ≤ (people × h/week × weeks). If it does not fit, cut
  Should/Could items before compressing estimates.
- Estimate high-uncertainty tasks as ranges (optimistic / likely / pessimistic) *(added)*.

**Gate:** total ≤ capacity; the reconciliation is documented.

### Step 5 — Interface Contracts (API / CLI / Events) *(added)*
**Why:** expanding a task into implementation is dangerous if the components do not know how to
talk to each other. Before coding, every point of contact between components must have an
explicit contract.

**What to define by interface type:**

| Type | The contract must include |
|---|---|
| **HTTP API** | Method + route, request and response JSON with types, required/optional fields, status codes, errors, authentication, pagination/idempotency where applicable |
| **CLI** | Command, arguments and flags (type, default, required), stdin/stdout, output format, exit codes |
| **Function / module** | Full typed signature, pre/postconditions, exceptions, side effects, performance requirements where applicable |
| **Events / messages** | Name, producer, consumers, payload schema, version, guarantees (ordering, at-least-once) |
| **Data / files** | Schema (JSON Schema, SQL DDL), encoding, validation rules |

**Rules:**
- **Single source of truth** in `docs/contracts/` or in code (OpenAPI, JSON Schema, Pydantic,
  Protobuf); tasks *reference* it, they do not copy it.
- Each contract carries **at least one valid and one invalid example** with its expected error.
- A **common error model** across the whole project (format, codes, messages).
- **Contract versioning:** a *breaking* change requires an ADR and a MAJOR bump.
- **Contract tests first:** the failing test of every task that produces or consumes an interface
  validates the contract; producer and consumer test against the same contract.

**Gate:** no task that produces or consumes an interface becomes *Ready* without its contract
referenced and approved.

### Step 6 — Expand each task into a file
Path: `implementation/sprint-N-slug/SN-TM-slug.md`. Fixed template:

```markdown
---
id: SN-TM
sprint: N
owner: <name>
effort_h: <total>
depends_on: [SN-TK, …]
status: todo
---
# SN-TM — <verb + artifact>

| Sprint | Owner | Effort (h, sum to total) | Dependencies | Related docs |
|--------|-------|--------------------------|--------------|--------------|

## Purpose
Why this task exists.

## Preconditions
What must be merged/available before starting.

## Interface Contract
Mandatory if the task produces or consumes an interface. Reference to the source contract plus a summary:
- **Input:** JSON / CLI arguments / function signature
- **Output:** JSON / stdout + exit code / return value
- **Errors:** cases and codes
- **Valid / invalid example**

## Essential Sub-tasks
Atomic (≤2 h), with hours and a code snippet where applicable:
- 4.1 Contract test + functional test, failing (1.5 h)
- 4.2 Minimal implementation (2 h)
- 4.3 Refactor + types/lint (1 h)

## Deliverables
Exact paths of created/modified files.

## Acceptance Criteria
Copied from the roadmap; pass/fail.

## Verification
Copy-pasteable commands (e.g. `uv run pytest …`, `ruff check .`, `mypy .`).

## Edge Cases & Pitfalls

## Risks / Scope Cuts
What gets cut if it slips.

## Definition of Done
- [ ] …
```

**Key rule:** every sub-task carries **its test first (TDD)** and **its hours**; sub-task hours sum
to the task's effort.
*(Added)* For non-code projects (thesis, reports, design), replace "test" with a
**verifiable review criterion** (checklist, rubric, validation with the advisor).

**Gate:** a new developer/agent can execute the task by reading only that file (plus the contract
it references).

### Step 7 — Index `implementation/README.md`
It must contain:
1. **Task Index:** table `ID → file → owner → hours → status`. *(Added)* If every task's YAML
   front matter is complete, the index can be **generated automatically**.
2. **Critical Path** in ASCII, e.g.:
   ```
   S1 ---+--> S3 --> S4      (critical: S1→S3→S4; S2 has slack but blocks S3)
   S2 ---+
   ```
3. **Cross-Cutting Rules:** TDD, 1 commit per task (`SN-TM: <message>`; ideally *Conventional
   Commits* to feed the changelog), type hints, no network in tests, determinism, branch/PR
   convention, code style.
4. **Document Control:** version, date, maintainers, change history.

**Plan lint *(added)*:** a simple script that validates the plan before starting and on every
change: sub-task hours sum to the task's, task hours sum to the sprint's, IDs are unique, all
dependencies exist and form a graph **with no cycles**, and links between documents are valid.

### Step 8 — Critical path and cuts
- State which sprints block which, and where there is slack.
- Define **cut triggers**: *"if a sprint slips >3 days → apply cut N"*
  (e.g. drop Pipfile, lower k=5→3, postpone configuration).
- Keep an **ordered list of cuts** (lowest to highest impact) so scope can be negotiated without
  breaking the date.
- **Stubs/fakes and feature flags *(added)*:** to avoid blocking parallel work, whoever consumes
  a not-yet-implemented interface works against a stub/fake generated from the contract
  (Step 5); it is replaced by the real implementation at integration.

### Step 9 — Execution and tracking
- **Progress log** (date, what was done, actual hours, blockers).
- **Technical debt backlog** at the end of the roadmap: `DT-01…` with status, location, effort,
  verification, and closure.
- **When closing a task:** tick the DoD + quality gates (`ruff` + `mypy` + `pytest --cov`, or
  those in the doc 06 table) + update `status` in the front matter.

### Step 10 — Close, release, and post-mortem *(added)*
Once the DoDs of all Must sprints are met:

1. **Freeze:** only fixes are accepted; verify all Musts are done and quality gates pass on the
   release branch.
2. **Changelog:** compile it (*Keep a Changelog* format: Added / Changed / Fixed / Removed /
   Security), starting from the commits and reviewing by hand; reference the `SN-TM` IDs.
3. **SemVer version:**
   - MAJOR: breaking changes in contracts (Step 5).
   - MINOR: new backward-compatible functionality.
   - PATCH: fixes.
   Use `-rc.N` for candidates; update the version in a single place and create the `vX.Y.Z` tag.
4. **Packaging** according to project type: Docker image (tagged with the version, not just
   `latest`), binary, wheel/npm package, installer. Verify with an **install smoke test in a clean
   environment**.
5. **Release checklist:** green build from scratch, smoke test OK, README/quickstart updated,
   release notes published, **rollback plan** defined.
6. **Draining debt into the next cycle:** review the `DT-xx` backlog; each item is closed,
   dropped with justification, or migrated to the next cycle's backlog with context (location,
   effort, impact). The same applies to unfinished tasks and applied cuts.
7. **Post-mortem** (`docs/postmortem-vX.Y.Z.md`): **estimated vs. actual** table per sprint, cuts
   applied and why, what worked, what didn't, and concrete actions for the next cycle (including
   buffer adjustment).

**Gate:** release published and verifiable, debt migrated, post-mortem archived.

---

## 3. Final plan delivery checklist

- [ ] Discovery approved (goal, success, out of scope)
- [ ] Constraints and MoSCoW priorities defined
- [ ] Complete spec with no critical TBDs, spikes resolved, repo structure and dependency rules defined
- [ ] Requirement→task→test traceability
- [ ] Roadmap with sprints, single owner, measurable criteria, DoD, and mitigations
- [ ] First sprint = walking skeleton; tasks ≤8 h and sub-tasks ≤2 h
- [ ] Estimate with buffer and reconciliation against capacity
- [ ] Interface contracts defined and referenced by the tasks that use them
- [ ] One file per task using the fixed template, YAML front matter, and TDD in every sub-task
- [ ] `implementation/README.md` with index, critical path, rules, and document control
- [ ] Plan lint passing (hours, IDs, dependencies with no cycles, links)
- [ ] Cut triggers and an ordered list of cuts
- [ ] Progress log and debt backlog initialized
- [ ] Close-out plan: changelog, SemVer, packaging, debt migration, and post-mortem

## 4. Agent conduct rules

1. **Strict order:** respect the steps and gates; if the user wants to skip one, warn them and
   record the assumption.
2. **Ask the minimum necessary** at the start (constraints, team, deadline); declare everything
   else as an explicit assumption.
3. **Nothing vague:** no "improve performance" or "finish soon"; always a number, threshold, or
   pass/fail.
4. **Contract-first:** do not expand a task that crosses a boundary between components without
   its contract defined.
5. **Consistency:** the hours in the task file, the roadmap table, and the reconciliation total
   must match. Verify before delivering.
6. **Incremental delivery:** present each layer to the user for validation before generating the
   next (spec → roadmap → implementation).
7. **Language and style:** use the user's language; kebab-case file names; stable IDs
   (`SN-TM`, `R#`, `DT-##`) that are never reused.
