# Whole-Project Audit Plan (via `code-review` skill)

The `code-review` skill (`.opencode/skills/quality/code-review/SKILL.md`, ID
`code-review`) is diff-scoped: `git diff <fixed-point>...HEAD`, max ~400 words per
axis. Do **not** point it at the whole repo in one run — the diff truncates and the
findings go shallow. Instead, run it once per slice below and aggregate.

Invoke each slice with: `load the code-review skill and review since <fixed-point>,
scoped to <paths>, spec is <spec-file>`.

## Stop-and-go gate (mandatory)

After each slice: STOP. Present that slice's `## Standards` / `## Spec` report,
tick its Status checkbox, and wait for an explicit user go (`go` / `continue` /
`next`) before touching the next slice. Never chain slices autonomously — one
slice per approval, no exceptions. Only mark a slice `[x]` after its report has
been presented; a fix pass does not unblock the next slice unless the user says so.

## Slices

| # | Slice | Paths | Spec source | Status |
|---|-------|-------|-------------|--------|
| 1 | Data foundation | `pyreach/parsers/ pyreach/osv/ pyreach/db/` | `documentation/implementation/sprint-1-data-foundation/` | [x] |
| 2 | AST engine | `pyreach/ast/ pyreach/loaders/` | `documentation/implementation/sprint-2-ast-engine/` | [x] |
| 3 | Call graph | `pyreach/callgraph/` | `documentation/implementation/sprint-3-callgraph-reachability/S3-T1..T4` | [x] |
| 4 | Reachability | `pyreach/reachability/` | `documentation/implementation/sprint-3-callgraph-reachability/S3-T5..T8` | [x] |
| 5 | Output + CLI | `pyreach/output/ pyreach/cli.py pyreach/config.py` | `documentation/implementation/sprint-4-sarif-cli/` | [ ] |
| 6 | Cross-cutting | `pyreach/exceptions.py pyreach/logger.py` | `AGENTS.md` §§11-12 (no task spec; Spec axis reports "no spec available") | [ ] |

## Per-slice recipe

```powershell
git rev-parse <fixed-point>                                    # must resolve
git diff <fixed-point>...HEAD -- <slice-paths>                 # must be non-empty, ideally < ~500 lines
```

Then load the skill with the fixed point, the path scope, and the spec file. Keep
findings under the skill's `## Standards` / `## Spec` headings; do not rerank across
axes — record the worst issue *within* each axis per slice.

## Variant: per-task commits

This repo commits one task per commit (`AGENTS.md` §11). Equivalent audit: one skill
run per task commit (`<sha>^...<sha>`) with that task's `S*-*.md` file as spec. More
runs, but each Spec axis is exact.

## Aggregation

After all slices: one line per slice (finding counts per axis + worst per axis), then
fix in order — blocking/security issues first, then per-slice improvements. For a
single-pass whole-repo over-engineering audit instead (dead code, bloat), use the
`ponytail-audit` skill, not this plan.
