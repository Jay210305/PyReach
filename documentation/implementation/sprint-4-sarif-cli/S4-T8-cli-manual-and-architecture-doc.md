# S4-T8 — Write CLI user manual and architecture overview doc

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Joint (Julio Centeno + Jose Alonso Yanez) |
| Effort | 4 h |
| Dependencies | All Sprint 4 tasks |
| Related docs | `01-project-overview.md`, `02-system-architecture.md`, `03-technical-specifications.md`, `09-cicd-integration.md`; roadmap M4 |

## Purpose

Deliver the documentation required for user adoption and academic defense: a practical CLI
manual and a concise architecture overview. It must be approved by Dr. Torres and Lidercom key
users (roadmap S4-T8).

## Preconditions

- Feature-complete CLI and CI templates.
- All prior documentation available for cross-referencing.

## Essential Sub-tasks

### 8.1 Write the CLI user manual (2 h)

Create `documentation/user-manual.md` (or `docs/user-manual.md`) containing:

1. **Installation**: uv and `pip install .` paths; Python 3.10+ requirement.
2. **First scan**: `pyreach sync-osv`, then `pyreach /path/to/project`.
3. **Command reference**: every option from `03-...md` §4 in a table, with defaults.
4. **Exit codes**: 0/1/2 and their CI meaning.
5. **Configuration**: full `.pyreach.yml` example and precedence rules.
6. **Output formats**: `sarif`, `json`, `text` with short samples.
7. **CI integration**: pointer to `ci/README.md` with the GitLab and Jenkins snippets.
8. **Troubleshooting**: the table from `07-...md` §3 plus common mistakes (missing DB, no
   entry points, performance).
9. **Data sovereignty note**: scans run fully offline; only `sync-osv` downloads data.

Keep it task-oriented with copy-paste commands; avoid re-deriving internal architecture here.

### 8.2 Write the architecture overview (1.5 h)

Create `documentation/architecture-overview.md` synthesizing `02-system-architecture.md`:

- Component diagram (input -> analysis core -> output).
- Data flow pipeline (the 6-step flow).
- Package/module map from `03-...md` §2.
- Key design decisions and rationale: local-first, SQLite, NetworkX, SARIF.
- Conservative over-approximation policy (R2) in plain language.
- Performance model and known limits (`max_depth`, memory).
- A "where to extend" section (new manifest parser, new output format, new entry-point rule).

Target audience: a new contributor or a Lidercom engineer maintaining the runner.

### 8.3 Cross-review and accuracy check (0.5 h)

- Verify every command in the manual actually runs against a fixture project.
- Verify the architecture doc names match the shipped modules (`pyreach/ast/resolver.py`,
  etc.).
- Fix any drift between docs and code; cite `file:line` where helpful.

## Deliverables

- `documentation/user-manual.md`
- `documentation/architecture-overview.md`
- Verified commands and reviewed drafts.

## Acceptance Criteria

- Approved by Dr. Torres and Lidercom key users. ✅ (roadmap S4-T8)
- Every documented command works as written.
- Manual covers installation, options, exit codes, config, CI, troubleshooting.

## Verification

- Run each manual command in a clean environment (or `tmp_path`) and confirm behavior.
- Have a reviewer follow the "first scan" section unaided.

## Edge Cases & Pitfalls

- Avoid screenshots that go stale; prefer text output.
- Document Windows-specific notes (PowerShell exit codes, path separators).
- Do not expose Lidercom-confidential repository names in the manual; use placeholders.
- Keep the manual versioned alongside the CLI; add a "last updated for vX.Y" line.

## Risks / Scope Cuts

- If time is short, ship the user manual (highest value) and keep the architecture doc as a
  one-page summary; both are required for the sprint DoD, so request advisor guidance before
  cutting.

## Definition of Done

- [ ] Both documents merged.
- [ ] All commands verified.
- [ ] Approval recorded from Dr. Torres and Lidercom users.
- [ ] Consistent with shipped module names and options.
