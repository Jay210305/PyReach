# 10 — Research references, availability, and dataset selection

**Verified against publicly accessible project descriptions on 2026-10-13**; exact asset paths, licensing and revisions must be checked and pinned by S0-T4. URLs below are acquisition references, not evidence that scans have run.

## Graph benchmark references
| Source | URL | Precise use | Applicability |
|---|---|---|---|
| PyAnalyzer (ICSE 2024 repository) | https://github.com/2024icse/PyAnalyzer | micro-benchmark B: 233 tests (=206 PyCG-origin +27), macro-benchmark C: 5 curated CGs | primary independent graph labels |
| PyCG original | https://github.com/vitsalis/PyCG | original micro corpus; baseline graph generator | overlapping data; 206 not added again |
| FASTEN Python call graph stitcher | https://github.com/fasten-project/pycg-stitch | `benchmark/micro`: 5-package graph stitching, `benchmark/macro`: Fabric stitched graph | cross-package graph quality; precomputed graph may differ from source export |
| SWARM-CG | https://github.com/secure-software-engineering/SWARM-CG | Python benchmark cases with ground truth, verify overlap and schema | supplementary; count only distinct eligible cases |

## Vulnerability symbol and independent labels
| Source | URL | Precisely limited use |
|---|---|---|
| Safety public model data | https://github.com/pyupio/safety-model-data | use openly licensed Python examples if actually present. README advertises large commercial feeds; no assumption full dataset is public |
| Vul4Py paper | https://arxiv.org/abs/2608.00692 | published 100 vulnerabilities/60 projects aimed at **repair**; verify if public cases/assets exist; do not infer function reachability from exploit test |
| OSV schema | https://ossf.github.io/osv-schema/ | dependency advisories; symbol-level certainty requires separately documented provenance |

## Real project cohorts (6 repository roots)
| Group | Project | URL | Observation |
|---|---|---|---|
| G1 | OWASP VulnReach lab `labs/python_vuln_app` | https://github.com/OWASP/VulnReach | candidate controlled target; verify manifest and scenario |
| G1 | PyGoat Django | https://github.com/adeyosemanputra/pygoat | intentionally vulnerable application code ≠ proven vulnerable dependency path |
| G2 | Django RealWorld API | https://github.com/gothinkster/django-realworld-example-app | old/archived dependency snapshot; **never execute legacy setup** |
| G2 | FastAPI full-stack template | https://github.com/fastapi/full-stack-fastapi-template | Python app in `backend/`, `uv.lock` workspace at root: verify scan root and manifest semantics |
| G3 | Saleor | https://github.com/saleor/saleor | large Django/GraphQL source, `pyproject.toml`+`uv.lock` |
| G3 | Wagtail | https://github.com/wagtail/wagtail | large Django CMS, Python packaging may be dynamic; package project vs app entry-point assumptions |

## Baseline tools (scope not identical)
- Package vulnerability coverage: https://github.com/pypa/pip-audit ; https://github.com/google/osv-scanner
- Graph generation (not CVE scanner): https://github.com/vitsalis/PyCG ; https://github.com/Technologicat/pyan
- Reachability / runtime-aware alternative: https://github.com/OWASP/VulnReach (substantial runtime/taint/route stack; only compare matching evidence/inputs).

## Important interpretation rules
- Baseline check that input versions and advisory snapshot actually match; tools may disagree because of database/update state rather than reachability.
- A CVE in the target repository does not establish an entry-point-to-vulnerable-function graph.
- `import yaml` and dependency name `PyYAML` illustrate package/import alias risk; mapping requires evidence.
- Public case references and conditional sources in this document are research inputs, not permission to redistribute data.

## Glossary
**Call edge:** canonical directed caller → callee function pair. **Snapshot:** frozen dataset, Git SHA, OSV SHA and tool versions. **Eligibility:** whether a test has enough output and reference evidence to be scored. **Abstention:** an indeterminate prediction, distinct from error or unsupported. **CI gate:** controlled execution exit 0 clean, 1 finding, 2 error as documented. **SARIF:** Static Analysis Results Interchange Format v2.1.0.
