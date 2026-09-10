# S1-T7 — Set up GitLab CI runner stage for pytest

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 2 h |
| Dependencies | S1-T6 (tests runnable locally) |
| Related docs | `09-cicd-integration.md` §2.1, §3.1; `08-testing-strategy.md` §7 |

## Purpose

Automate quality gates so every push runs the test suite and blocks merges on failure.
This is the foundation for the security stage added in Sprint 4.

## Preconditions

- A GitLab project with at least one available runner (shared or `lidercom-local-runner`).
- `pyproject.toml` and a working `poetry install --with dev`.

## Essential Sub-tasks

### 7.1 Create `.gitlab-ci.yml` with stages and caching (0.5 h)

```yaml
stages:
  - test

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

default:
  image: python:3.10-slim

test:
  stage: test
  before_script:
    - pip install poetry
    - poetry config virtualenvs.create false
    - poetry install --with dev
  script:
    - poetry run pytest -m "not performance" --cov=pyreach --cov-report=xml --cov-report=term --cov-fail-under=80
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
    key: "$CI_COMMIT_REF_SLUG"
    paths:
      - .cache/pip
      - .venv/
```

### 7.2 Configure Poetry inside CI (0.5 h)

- Pin the Poetry version used locally to avoid lockfile drift (`pip install poetry==1.7.*`).
- If the project only has `pyproject.toml` without a Poetry lock yet, generate and commit
  `poetry.lock` first.
- Ensure `poetry install` does not create a venv (`virtualenvs.create false`) so `pytest` is
  on the image PATH.

### 7.3 Add branch protection / merge gating (0.5 h)

- In GitLab: Settings -> Merge requests -> require pipeline success before merge.
- Mark the `test` job as required.
- Document the setting in the MR description (this is a repo setting, not a file).

### 7.4 Add a lint job (optional but recommended) (0.25 h)

```yaml
lint:
  stage: test
  script:
    - poetry run ruff check pyreach tests
    - poetry run mypy pyreach
```

Keep `allow_failure: false` so lint errors block merge (`10-risk-and-contingency-plan.md` §6).

### 7.5 Verify the pipeline (0.25 h)

- Push a trivial failing test in a branch; confirm the pipeline fails and merge is blocked.
- Remove the failing test; confirm green.
- Capture a screenshot/link of the successful pipeline for the sprint review.

## Deliverables

- `.gitlab-ci.yml`
- `poetry.lock` (if not already present)
- Documented branch-protection configuration.

## Acceptance Criteria

- Pipeline runs on push; failure blocks merge. ✅ (roadmap S1-T7)
- Coverage report is published as a Cobertura artifact.
- Lint/type checks are part of the gate.

## Verification

- Push to a feature branch and observe the GitLab pipeline.
- Locally reproduce: `poetry run pytest -m "not performance" --cov=pyreach --cov-fail-under=80`.

## Edge Cases & Pitfalls

- `coverage: '/TOTAL.../'` regex must match pytest-cov's output format; verify against the
  actual line, not an assumed layout.
- Poetry lockfiles are platform-sensitive; the CI image (`python:3.10-slim`, Linux) may resolve
  differently from Windows dev machines. If lock generation differs, use `poetry install`
  without a committed lock or add a Linux lock job.
- Cache `.venv/` only if installs are slow; a stale cache can mask dependency changes — bump
  the cache key when `poetry.lock` changes.

## Risks / Scope Cuts

- If no GitLab runner is available, fall back to a GitHub Actions workflow with equivalent
  steps and document the substitution (roadmap allows "GitLab or Jenkinsfile").

## Definition of Done

- [ ] `.gitlab-ci.yml` merged and green.
- [ ] Merge is blocked on failing tests.
- [ ] Coverage artifact present.
- [ ] Pipeline link recorded in the sprint review notes.
