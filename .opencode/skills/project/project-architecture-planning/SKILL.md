---
name: project-architecture-planning
description: Plan Fulbo architecture and delivery work across frontend, backend, database, integrations, and documentation. Use for implementation plans, technical decisions, or architectural changes; not for routine code edits.
---

# Fulbo architecture and planning

Use `docs/` as the source of durable project knowledge:

- `docs/architecture/` describes the implemented system.
- `docs/plans/current/` contains active work.
- `docs/plans/completed/` contains only verified, dated milestones.
- `docs/decisions/` records consequential technical choices.

## Planning rules

- Separate what is in source today from planned or dependency-installed capabilities. Fulbo's UI is more complete than its end-to-end backend integration.
- Break work at real contracts: database schema, NestJS API module, frontend service/client state, and verification.
- Identify authorization, migration, conflict, and external-service risks before estimating a feature.
- Record a decision when it changes a durable system boundary, not for routine implementation choices.

## Completion

A milestone is complete only after its acceptance checks, migration impact, API behavior, and test evidence are recorded. Keep unverified work in `plans/current/` rather than presenting it as completed.
