---
name: laya
description: Use the local Laya decision model as a quality gate for implementation plans and test claims. Call the fulbo-laya MCP tools (validate_plan, laya_status) before treating a plan as ready or a test suite as meaningful. Laya judges; it does not generate. Use whenever you write an implementation plan, claim a change is complete, or evaluate whether tests meaningfully validate behavior.
---

# Laya quality gate

Laya (https://github.com/NandhaKishorM/laya) is a local, non-autoregressive
decision engine wired into this project as the `fulbo-laya` MCP server. It
answers typed questions (`choice`, `score`, `noul`) over a text state in a
single forward pass. It does not generate text and it does not write plans or
tests. It is a **gate**: it decides whether work you already produced is good
enough to proceed.

## When to use it

- Before writing a plan to `docs/plans/current/`, validate it.
- Before claiming a task is complete, validate the plan that produced it.
- When you have written tests, use the same tool to judge whether the tests
  meaningfully validate the behavior (see "Test claims" below).

## Tools (server `fulbo-laya`)

| Tool | Purpose |
| --- | --- |
| `laya_status` | Report whether Laya is installed/loadable and the resolved settings. Call this first to know whether the gate is even available. |
| `validate_plan` | Validate a plan. `plan` (required), optional `tasks`, `context`, `min_confidence`. |

`validate_plan` derives tasks from markdown headings or list items when `tasks`
is omitted. It returns:

- `status`: `passed`, `failed`, `inconclusive`, or `unavailable`
- per-task `atomic`, `specific`, `self_contained`, `ambiguity` + `verdict`
- `issues`, `guidance`

Only `passed` counts as validation. `inconclusive` means Laya answered below
its confidence floor. `unavailable` means the model is not installed or failed
to load.

## Workflow

1. **Check availability.** Call `laya_status`. If it reports `laya_available:
   false`, the gate is unavailable: do not pretend otherwise.
2. **Validate the plan.** Write the plan so a normal agent can follow it without
   Laya, then call `validate_plan` with the plan text and the explicit task
   list when you have one.
3. **React to the verdict.**
   - `passed` — proceed. Record `laya_validation: passed` in the plan header.
   - `failed` — revise or subdivide the flagged tasks (make them atomic,
     specific, self-contained) and call `validate_plan` again.
   - `inconclusive` / `unavailable` — this is **not** validation. Continue only
     if you accept the risk, and record `laya_validation: skipped (unavailable)`
     (or `inconclusive`) with the reason. Never present it as Laya-validated.
4. **Record the outcome** in the plan header, per `AGENTS.md`.

## What Laya can and cannot catch

Laya checks plan quality through typed questions: whether the plan is
decomposed into essential units, and whether each task is atomic, specific, and
self-contained. Map your concern to a typed question over the plan text.

Laya can help surface:

- missing essential tasks (decomposition gaps),
- tasks that bundle multiple outcomes (non-atomic),
- vague or ambiguous task statements,
- plans that assume context the executor does not have,
- superficial "complete" claims with no acceptance criteria.

Laya does **not** run code, read the repository, or execute tests. It judges
only the text you hand it. Its base checkpoints are near chance zero-shot on
typed-decisions; treat results as advisory and confidence-gated. For reliable
gating, fine-tune Laya on your own plans and/or raise `LAYA_MIN_CONFIDENCE`.

## Test claims

Laya has no dedicated "validate tests" tool. To gate a test claim, hand the
relevant test descriptions plus the behavior they are supposed to verify to
`validate_plan` as the `plan` text, and use `context` to state the production
behavior. Laya will judge whether the described checks are specific and
meaningful against that context — but it cannot execute them. It is a weaker
gate than plan validation: do not treat a `passed` here as proof the tests
actually pass or genuinely exercise the code. Run the tests yourself.

## Honesty rule

Never describe a plan or test as Laya-validated unless `validate_plan` returned
`status: passed`. If Laya is unavailable, say so explicitly and record
`laya_validation: skipped (unavailable)`.
