# S1-T7 — Set up GitLab CI runner stage for pytest

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 2 h |
| Dependencies | S1-T6 (tests runnable locally) |
| Related docs | `09-cicd-integration.md` §2.1, §3.1; `08-testing-strategy.md` §7; `AGENTS.md` (uv commands) |

## Purpose

Automate quality gates so every push runs the test suite and blocks merges on failure.
This is the foundation for the security stage added in Sprint 4. The project uses **uv** for
dependency management and the local `.venv` as the project environment.

## Preconditions

- A GitLab project with at least one available runner (shared or `lidercom-local-runner`).
- Root `pyproject.toml` and committed `uv.lock` (created during environment bootstrap).
- Local verification works: `uv sync` then `uv run pytest`.

## Essential Sub-tasks

### 7.1 Create `.gitlab-ci.yml` with stages and caching (0.5 h)

```yaml
stages:
  - test

variables:
  UV_CACHE_DIR: "$CI_PROJECT_DIR/.cache/uv"

default:
  image: python:3.10-slim

test:
  stage: test
  before_script:
    - pip install uv
    - uv sync
  script:
    - uv run pytest -m "not performance" --cov=pyreach --cov-report=xml --cov-report=term --cov-fail-under=80
  coverage: '/TOTAL\s+\d+\s+\d+\s+(\d+)%/'
  artifacts:
    when: always
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    paths:
      - coverage.xml
  cache:
    key:
      files:
        - uv.lock
    paths:
      - .cache/uv
```

### 7.2 Configure uv inside CI (0.5 h)

- Install `uv` from PyPI (`pip install uv`) or use the official `ghcr.io/astral-sh/uv` image.
- `uv sync` creates/uses `.venv` and installs the locked runtime + dev dependencies. Pin the
  lockfile by committing `uv.lock`; uv fails the build if `pyproject.toml` and `uv.lock`
  drift (`--locked` can enforce this).
- Prefer `uv sync --locked` in CI so an out-of-date lock is an explicit error.
- `uv run` executes commands inside `.venv` without manual activation.

### 7.3 Add branch protection / merge gating (0.5 h)

- In GitLab: Settings -> Merge requests -> require pipeline success before merge.
- Mark the `test` job as required.
- Document the setting in the MR description (this is a repo setting, not a file).

### 7.4 Add a lint/type job (optional but recommended) (0.25 h)

```yaml
lint:
  stage: test
  script:
    - uv run ruff check pyreach tests
    - uv run mypy pyreach
```

Keep `allow_failure: false` so lint errors block merge (`10-risk-and-contingency-plan.md` §6).

### 7.5 Verify the pipeline (0.25 h)

- Push a trivial failing test in a branch; confirm the pipeline fails and merge is blocked.
- Remove the failing test; confirm green.
- Capture a screenshot/link of the successful pipeline for the sprint review.

## Deliverables

- `.gitlab-ci.yml`
- `uv.lock` (committed; created during bootstrap)
- Documented branch-protection configuration.

## Acceptance Criteria

- Pipeline runs on push; failure blocks merge. ✅ (roadmap S1-T7)
- Coverage report is published as a Cobertura artifact.
- Lint/type checks are part of the gate.

## Verification

- Push to a feature branch and observe the GitLab pipeline.
- Locally reproduce: `uv sync` then
  `uv run pytest -m "not performance" --cov=pyreach --cov-fail-under=80`.

## Edge Cases & Pitfalls

- `coverage: '/TOTAL.../'` regex must match pytest-cov's output format; verify against the
  actual line, not an assumed layout.
- The dev venv is Python 3.14 while CI runs 3.10; `uv.lock` is universal, but ensure the code
  stays compatible with `requires-python = ">=3.10"` (no 3.11+ only syntax).
- Cache `.cache/uv` (download cache), keyed on `uv.lock`; do not cache `.venv/` (uv recreates
  it quickly and a stale venv can mask dependency changes).
- If `uv` is unavailable in the runner image, use the official
  `ghcr.io/astral-sh/uv:python3.10-bookworm` image instead of installing it.

## Risks / Scope Cuts

- If no GitLab runner is available, fall back to a GitHub Actions workflow with equivalent uv
  steps and document the substitution (roadmap allows "GitLab or Jenkinsfile").

## Definition of Done

- [ ] `.gitlab-ci.yml` merged and green.
- [ ] `uv.lock` committed and CI uses `--locked`.
- [ ] Merge is blocked on failing tests.
- [ ] Coverage artifact present.
- [ ] Pipeline link recorded in the sprint review notes.
