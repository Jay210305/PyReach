# Code Review Audit — Reports

Two-axis (Standards x Spec) review outputs produced with the `code-review` skill
(`.opencode/skills/quality/code-review/`), following
`documentation/code-review-audit-plan.md`.

Corrections applied to the findings are recorded in
**[remediation.md](remediation.md)** (one entry per finding, per slice).

## Run parameters

- Fixed point: `c03e073` (initial documentation).
- Diff form: `git diff c03e073...HEAD -- <slice-paths>`, HEAD at run time `1299c81`
  ("Sprint 3 completed", committed before the audit so slices 3-4 are diff-based).
- Slice 5 (output/CLI): **skipped** — no code exists yet (`pyreach/output/`, `cli.py`,
  `config.py` unimplemented).
- Slice 6 (cross-cutting): **partial** — only `exceptions.py` exists; `logger.py` missing.
- Gate: stop-and-go per slice; a slice is ticked in the plan only after its report was
  presented.

## Progress

| # | Slice | Report | Standards findings (worst) | Spec findings (worst) |
|---|-------|--------|----------------------------|------------------------|
| 1 | Data foundation | [slice-1-data-foundation.md](slice-1-data-foundation.md) | 9 — `last_affected` stored as exclusive `fixed` (false negative, breaches AGENTS.md §1) | 12 — same inversion + multi-range overwrite in `osv_json.py:81-91`, locked in by a test |
| 2 | AST engine | slice-2-ast-engine.md | 7 — accidental `resolver.py,cover` artifact tracked in git; unguarded file reads in `build_file()` | 9 — relative imports in `__init__.py` resolve one level too high (`symbols.py:55-60`), masked by tests |
| 3 | Call graph | [slice-3-callgraph.md](slice-3-callgraph.md) | 9 — wrong/contradictory comments; `SENTINEL` node type outside §6 contract | 6 — IMPORT edges never created + latent `KeyError`; nested-lambda false negative |
| 4 | Reachability | [slice-4-reachability.md](slice-4-reachability.md) | 8 — bare `ValueError` vs `ConfigError`; symbol-keyed dict drops colliding vulns | 9 — global "dynamic anywhere" defeats matrix row 4; `package_imported` reads whole graph |
| 5 | Output + CLI | [slice-5-output-cli.md](slice-5-output-cli.md) — unticked, no code to review | 0 — no code | 0 — no code; S4-T1..T8 backlog pending |
| 6 | Cross-cutting | slice-6-cross-cutting.md | pending | pending (partial scope) |

## Aggregation rule

Findings are kept per axis and per slice; they are not reranked across axes. Fix order
after all slices: blocking/security first, then per-slice improvements.
