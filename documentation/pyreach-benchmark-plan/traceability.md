# Requirement → Task → Test traceability (single table)

| Requirement | Tasks | Verifiable proof/test |
|---|---|---|
| REQ-01 | S0-T4 | `test_source_lock.py::test_pinned_license_and_hash` |
| REQ-02 | S0-T1,S0-T2,S0-T3 | `test_cli_sarif.py::test_walk_skeleton` |
| REQ-03 | S1-T1,S1-T2,S1-T3 | `test_graph_cases.py::test_233_accounted` |
| REQ-04 | S1-T4 | `test_macro.py::test_five_accounted` |
| REQ-05 | S1-T5 | `test_swarm.py::test_no_overlap_and_eligible` |
| REQ-06 | S2-T1,S2-T2 | `test_fasten.py::test_micro_macro_denominator` |
| REQ-07 | S2-T3,S2-T4 | `test_reachability.py::test_36_labels_reviewed` |
| REQ-08 | S2-T5 | `test_vul4py.py::test_eligibility_requires_symbol` |
| REQ-09 | S3-T1,S3-T2,S3-T3 | `test_project_catalog.py::test_six_pinned_or_blocked` |
| REQ-10 | S3-T4 | `test_baselines.py::test_comparison_scope` |
| REQ-11 | S4-T1 | `test_cli_sarif.py::test_exit_and_offline` |
| REQ-12 | S4-T2 | `test_report.py::test_three_repeats_and_denominators` |
| REQ-13 | S4-T3,S4-T4 | `test_report.py::test_signed_release_evidence` |
| REQ-14 | S0-T2,S4-T4 | `python3 scripts/validate_plan.py` |
| REQ-15 | S2-T3 | `test_symbols.py::test_public_sample_provenance` |
| REQ-16 | — | Could; deferred with explicit new scope if licensing granted |
| REQ-17 | — | Won't; audit QG-08 enforces no untrusted execution |

Tests are **target artifact names** to create in tasks, not claims that files already exist. Requirement-to-task rows correspond to `01-overview.md`, task IDs `implementation/README.md`, and acceptance criteria in `04-implementation-roadmap.md`.
