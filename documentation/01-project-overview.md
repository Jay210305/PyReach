# PyReach - Project Overview

## Vision

PyReach is a static reachability analysis engine designed to reduce vulnerability alert fatigue in Python software projects by determining whether reported CVEs in transitive dependencies are actually reachable from application code. Unlike traditional Software Composition Analysis (SCA) tools that report every vulnerable package indiscriminately, PyReach constructs precise call graphs and performs interprocedural path analysis to filter out non-exploitable alerts with a target reduction rate of approximately 70%.

## Mission

Enable development teams at Lidercom Peru S.A.C. (and similar organizations) to focus on genuinely exploitable vulnerabilities by providing a fast, fully local, data-sovereign analysis tool that integrates seamlessly into CI/CD pipelines via SARIF v2.1.0 output and exit-code quality gates.

## Problem Statement

Modern Python applications depend on hundreds of transitive libraries. Traditional SCA scanners (e.g., pip-audit, Safety, Snyk) flag every known vulnerability in the dependency tree, regardless of whether the vulnerable code path is ever invoked by the host application. This produces:

- **Alert fatigue**: Developers ignore or dismiss notifications en masse.
- **Wasted triage effort**: Teams spend ~16 person-hours per month manually reviewing non-exploitable CVEs.
- **Delayed remediation**: Real critical vulnerabilities hide among hundreds of false positives.
- **Compliance friction**: ISO/IEC 27001:2022 Control A.8.12 requires vulnerability management without cloud data exposure.

## Solution Approach

PyReach solves this through **static reachability analysis**:

1. Parse Python dependency manifests (`requirements.txt`, `Pipfile.lock`).
2. Ingest vulnerability advisories from local OSV (Open Source Vulnerability) database snapshots.
3. Build an **Abstract Syntax Tree (AST)** representation of application and library code.
4. Construct an **interprocedural Call Graph** using NetworkX.
5. Run a **bounded reachability algorithm** (max depth k=5) from application entry points to vulnerable symbols.
6. Classify each vulnerability as:
   - **Reachable**: There is a static call path from an entry point to the vulnerable function.
   - **Not Reachable**: No static path exists; the alert can be safely deprioritized.
   - **Potentially Reachable**: Dynamic constructs (`eval`, `exec`, `getattr` chains, import hooks) prevent definitive analysis; conservative over-approximation to avoid false negatives.
7. Serialize results as **SARIF v2.1.0** for ingestion by CI/CD dashboards and IDEs.

## Target Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Alert reduction rate | >= 70% | Compare raw SCA alerts vs. PyReach-filtered alerts on 5 Lidercom microservices |
| Scan performance | < 45 seconds per repository | CI/CD runner timer on representative microservices |
| False negative rate | 0% critical | Manual audit of all "Not Reachable" classifications for high/critical CVEs |
| Data sovereignty | 0 bytes to cloud | Network traffic monitoring during scans |
| Test coverage | >= 80% | pytest-cov report |

## Success Criteria

1. **Functional**: The tool correctly parses manifests, maps OSV advisories to installed versions, builds call graphs, and classifies reachability for >= 90% of vulnerabilities in standard Python code.
2. **Performance**: Average scan time under 45s on Lidercom's largest microservice (~15 direct deps, ~80 transitive deps).
3. **Integration**: SARIF output is successfully consumed by GitLab CI security dashboard and local review tooling.
4. **Adoption**: Lidercom developers reduce manual triage time by at least 70% during weekly security sessions.
5. **Compliance**: Full local execution with no external API calls during analysis, satisfying data-sovereignty policies.

## Scope Boundaries

### In Scope
- Manifest parsing: `requirements.txt` (primary), `Pipfile.lock` (secondary).
- OSV advisory ingestion and local SQLite storage.
- AST-based call graph construction for Python 3.10+ syntax.
- Intraprocedural and interprocedural reachability analysis (max depth 5).
- Conservative heuristic for dynamic metaprogramming patterns.
- SARIF v2.1.0 serialization.
- CLI with configurable entry points, depth, and output path.
- CI/CD quality gate via exit codes (0 = pass, 1 = reachable CVEs found, 2 = config error).

### Out of Scope (Accepted Trade-offs)
- Dynamic analysis or runtime instrumentation.
- Symbolic execution.
- Automatic code patching / auto-remediation.
- Support for `conda`, `poetry.lock`, or `setup.py` as primary manifests (post-MVP).
- Handling of C-extension native code (beyond Python AST boundaries).
- Cloud-based or SaaS execution models.

## Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| Sponsor / Advisor | Dr. Nestor Torres Gamarra | Methodological supervision, scope authorization |
| Project Manager / Analyst | Julio Centeno Leon | Requirements, AST engine, symbol tables, data modeling |
| Project Manager / Developer | Jose Alonso Yanez Mejia | Call graphs, reachability algorithm, SARIF, CI/CD |
| Quality Leads (Key Users) | Luis Espinoza, Andry Caceres | Heuristic validation, TDD audit, ISO 27001 compliance |

## Regulatory & Compliance Context

- **ISO/IEC 27001:2022 Control A.8.12**: Management of technical vulnerabilities. PyReach supports this by providing local, auditable vulnerability assessment.
- **Data Sovereignty**: Fully on-premise execution; zero external data transmission during analysis.
- **Open Source Stack**: Python 3.10+, uv, SQLite, NetworkX, pytest — no proprietary runtime licenses required.

## References

- Pashchenko, I., et al. (2022). Vuln4Real: A methodology for counting actually vulnerable dependencies. *IEEE TSE*, 48(5), 1592-1609.
- Salis, V., et al. (2021). PyCG: Practical call graph generation in Python. *ICSE 2021*, 1646-1657.
- OASIS. (2019). *Static Analysis Results Interchange Format (SARIF) Version 2.1.0*.
- OpenSSF. (2023). *Open Source Vulnerability (OSV) Schema Documentation* v1.6.0.
- Hagberg, A. A., et al. (2008). Exploring network structure with NetworkX. *SciPy 2008*, 11-15.

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
