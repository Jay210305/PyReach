# Risk and Contingency Plan

## 1. Risk Register

This document consolidates the technical, business, and management risks identified during Phase 1 analysis with specific contingency actions for Phase 2 implementation.

### Risk Matrix Summary

| ID | Risk | Category | Probability | Impact | Risk Score |
|----|------|----------|-------------|--------|------------|
| R1 | Combinatorial explosion in NetworkX graphs | Technical | Medium (20%) | High | 0.20 |
| R2 | False negatives from dynamic metaprogramming | Technical | Medium (25%) | Medium | 0.25 |
| R3 | SARIF v2.1.0 schema rejection | Technical | Low (10%) | High | 0.10 |
| R4 | Delay accessing Lidercom microservices | Business | Medium (20%) | High | 0.20 |
| R5 | Corporate sponsor deprioritization | Business | Low (5%) | High | 0.05 |
| R6 | Academic overload during midterms | Management | High (30%) | Medium | 0.30 |
| R7 | Time slippage from AST complexity | Management | Medium (10%) | High | 0.10 |

*Risk Score = Probability x Impact (normalized 0-1)*

## 2. Detailed Risk Responses

### R1: Combinatorial Explosion in NetworkX Graphs

**Description**: Densely coupled dependency trees (e.g., large frameworks like Django or data science stacks) may produce graphs with thousands of nodes and edges, causing excessive memory consumption or traversal time.

**Trigger Conditions**:
- Graph nodes exceed 10,000.
- Scan time exceeds 45 seconds on medium-sized projects.
- Runner reports OOM (Out Of Memory) kills.

**Mitigation Strategies**:
1. **Depth Limiting**: Hard cap at `k=5` hops for reachability traversal. Do not make configurable beyond 7.
2. **Lazy Loading**: Only parse ASTs for packages that have known vulnerabilities in the OSV database. Skip unaffected packages entirely.
3. **Graph Pruning**: Remove leaf nodes (functions with no outgoing calls) that are not vulnerable symbols before reachability analysis.
4. **Memory-Optimized Structures**: Use `networkx.DiGraph` (not `MultiDiGraph`). Store edge attributes only when necessary.
5. **Streaming Alternative**: If memory still exceeds 2GB, fall back to SQLite-backed traversal instead of full in-memory graph.

**Contingency Plan**:
- If R1 triggers during Sprint 3, immediately implement lazy loading (estimated +4 hours).
- If still failing, reduce max_depth default from 5 to 3 and document the precision trade-off.

### R2: False Negatives from Dynamic Metaprogramming

**Description**: Python's dynamic features (`eval`, `exec`, `getattr`, dynamic imports, monkey-patching) make static analysis incomplete. A vulnerable function reached via dynamic means may be classified as `NOT_REACHABLE`.

**Trigger Conditions**:
- Post-deployment discovery of an exploited vulnerability that PyReach marked `NOT_REACHABLE`.
- Manual audit reveals dynamic call chains in application code.

**Mitigation Strategies**:
1. **Preventive Heuristic**: Any call chain containing a `DYNAMIC` edge or unresolved import automatically classifies the target as `POTENTIALLY_REACHABLE`, never `NOT_REACHABLE`.
2. **Pattern Detection**: Maintain an explicit list of dynamic patterns (see AST Engine document) and flag them during graph construction.
3. **Audit Mode**: Provide `--audit-dynamic` flag that lists all `POTENTIALLY_REACHABLE` classifications with reasoning for human review.

**Contingency Plan**:
- If a false negative is discovered during Phase 3 validation, immediately add the missed pattern to the heuristic list and release a patch (Sprint 4 buffer + 2 days).

### R3: SARIF v2.1.0 Schema Rejection

**Description**: CI/CD platforms or downstream tools reject PyReach output because it violates the SARIF schema or uses unsupported properties.

**Trigger Conditions**:
- GitLab Security Dashboard fails to parse the artifact.
- `jsonschema` validation fails in unit tests.
- VS Code SARIF Viewer shows errors.

**Mitigation Strategies**:
1. **TDD Validation**: From Sprint 4 day 1, every SARIF output test validates against the official OASIS jsonschema.
2. **Conservative Properties**: Place all custom metadata (`reachability`, `cveId`, etc.) inside `result.properties`, never modifying required SARIF fields.
3. **Reference Implementations**: Compare output structure against sample SARIF files from `github/codeql-action` and `microsoft/sarif-sdk`.

**Contingency Plan**:
- If rejection occurs, fallback to pure `json` output format while fixing SARIF serialization. CI gate can temporarily parse JSON instead of SARIF (1-day workaround).

### R4: Delay Accessing Lidercom Microservices

**Description**: Lidercom's operational security policies or scheduling conflicts may prevent access to real microservice code for integration testing and validation.

**Trigger Conditions**:
- No VPN or repository access granted by Week 11.
- NDAs or security clearance paperwork pending.

**Mitigation Strategies**:
1. **Containerized Replicas**: Maintain Docker-based synthetic microservices in `tests/fixtures/projects/` that mimic Lidercom's architecture (Flask/FastAPI with similar dependency trees).
2. **Public Analogues**: Use open-source Python projects with comparable dependency profiles as secondary validation targets.
3. **Early Coordination**: Schedule access meetings with Lidercom IT during Sprint 2 (Week 7), two weeks before needed.

**Contingency Plan**:
- If real access is unavailable by Week 13, conduct Phase 3 evaluation entirely on containerized replicas and public analogues. Document the limitation transparently in the final report.

### R5: Corporate Sponsor Deprioritization

**Description**: Lidercom management may lose interest or reallocate resources, withdrawing support for the project.

**Trigger Conditions**:
- Cancelled meetings or unanswered emails.
- Budget or access revocation.

**Mitigation Strategies**:
1. **Biweekly Demos**: 15-minute sprint review demonstrations to general management showing concrete progress (parsed manifests, built graphs, detected CVEs).
2. **Value Articulation**: Frame every demo in terms of hours saved and risk reduced, not technical milestones.
3. **Academic Independence**: The capstone project can complete successfully using synthetic data if corporate access is lost; Lidercom validation is desirable but not academically mandatory.

**Contingency Plan**:
- If sponsorship is withdrawn before Week 10, pivot to publicly available Python projects for validation. Adjust final report scope accordingly.

### R6: Academic Overload During Midterm Exams

**Description**: University midterm exams (Weeks 8 and 16) reduce available engineering hours, risking sprint delays.

**Trigger Conditions**:
- Team availability drops below 50% during exam weeks.
- Sprint deliverables incomplete at review.

**Mitigation Strategies**:
1. **Buffer Allocation**: Reserve 3 days of buffer per sprint. Schedule heavy tasks (AST engine, Call Graph) outside Weeks 8 and 16.
2. **Front-Loading**: Complete highest-risk tasks (S2-T1 AST self-study, S3-T1 NetworkX study) before Week 8.
3. **Task Splitting**: Break large tasks into independent subtasks so one team member can continue if the other is studying.

**Contingency Plan**:
- If both team members are simultaneously overloaded, apply scope negotiation: postpone `Pipfile.lock` support or reduce test coverage target from 80% to 70% for non-critical modules.

### R7: Time Slippage from AST Complexity

**Description**: Building a correct AST-based call graph for Python proves more complex than estimated, consuming Sprint 2 and 3 buffer.

**Trigger Conditions**:
- Sprint 2 ends with import resolution failing on >20% of real-world modules.
- Symbol table construction takes >15 hours instead of estimated 10.

**Mitigation Strategies**:
1. **Mitigation M1**: Front-load AST self-study (16 hours in Sprint 2).
2. **Library Reuse**: Reference PyCG schemas and algorithms rather than inventing from first principles.
3. **Simplification Fallback**: Support only absolute imports and simple relative imports. Defer star-import resolution and namespace packages.

**Contingency Plan**:
- If slippage exceeds 15% of Sprint 2 effort, formally invoke the scope negotiation clause: drop `Pipfile.lock` support entirely and focus all remaining effort on `requirements.txt` + absolute imports.

## 3. Scope Negotiation Protocol

The team formally adopts the following escalation protocol when a sprint delay exceeds 15% of planned effort:

```
Delay Detected
    |
    v
[1] Inform Advisor (Dr. Torres) within 24 hours
    |
    v
[2] Assess which protected variable is threatened: TIME
    |
    v
[3] Identify scope items to trim (negotiable variable)
    |
    v
[4] Document decision in sprint retrospective notes
    |
    v
[5] Adjust remaining sprint backlog and notify stakeholders
```

### Negotiable Scope Items (Priority Order for Cutting)

1. **Pipfile.lock support** (Sprint 1) — Lowest business value for Lidercom (they use `requirements.txt`).
2. **Star-import resolution** (Sprint 2) — Affects accuracy on uncommon patterns.
3. **`.pyreach.yml` configuration file** (Sprint 4) — CLI flags are sufficient for MVP.
4. **Call graph caching to SQLite** (Sprint 3) — Performance optimization, not correctness.
5. **HTML report generation** (not in current scope) — Future enhancement.

## 4. Communication Plan

| Stakeholder | Frequency | Channel | Content |
|-------------|-----------|---------|---------|
| Dr. Nestor Torres Gamarra | Weekly | Email + in-person | Sprint status, blockers, scope changes |
| Lidercom Key Users (Luis, Andry) | Biweekly | Teams/Zoom | Demo of working features, feedback collection |
| Lidercom General Management | Biweekly | 15-min presentation | Progress metrics, business value tracking |
| Internal Team | Daily | WhatsApp / Discord | Task coordination, quick questions |

## 5. Budget Contingency

**Contingency Reserve**: S/ 300.00 (8.6% of total budget), quantified via EMV analysis.

**Allocation Rules**:
- R1 (Graph explosion): S/ 60.00 — Infrastructure upgrade or extra compute hours.
- R2 (Dynamic false negatives): S/ 50.00 — Additional testing and validation time.
- R3 (SARIF rejection): S/ 40.00 — Tooling and schema validation resources.
- R4 (Access delay): S/ 50.00 — Docker/containerization infrastructure.
- R5 (Deprioritization): S/ 30.00 — Public project evaluation substitutes.
- R6 (Academic overload): S/ 30.00 — Buffer time compensation.
- R7 (AST slippage): S/ 40.00 — Additional study materials or mentoring.

**Release Authority**: Any contingency expenditure >S/ 50.00 requires approval from Dr. Torres.

## 6. Quality Assurance Gates

Before each sprint can be considered complete, the following gates must pass:

1. **Code Review**: All merged code reviewed by the other team member.
2. **Test Coverage**: pytest-cov >=80% on new code (negotiable down to 70% only with advisor approval).
3. **Linting**: `ruff` and `mypy` pass with zero errors.
4. **SARIF Validity**: If SARIF output is in scope for the sprint, it must validate against the jsonschema.
5. **Performance**: If a module is performance-critical, it must pass the benchmark in `tests/performance/`.

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
