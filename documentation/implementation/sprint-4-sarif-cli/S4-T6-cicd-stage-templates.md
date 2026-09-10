# S4-T6 — Build CI/CD stage templates (GitLab CI job, Jenkins stage)

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 6 h |
| Dependencies | S4-T2, S4-T3, S4-T4, S1-T7 |
| Related docs | `09-cicd-integration.md` §2, §5, §7; `03-technical-specifications.md` §4 |

## Purpose

Deliver copy-paste-ready pipeline templates that run PyReach as a security quality gate and
publish SARIF to GitLab/Jenkins. This is what makes the project valuable to Lidercom.

## Preconditions

- CLI and SARIF output working end to end.
- Existing `.gitlab-ci.yml` from S1-T7.
- A pre-seeded OSV DB path convention (`/opt/pyreach/osv.db`).

## Essential Sub-tasks

### 6.1 Author the GitLab CI template (2 h)

Create `ci/gitlab/.pyreach-scan.yml` (an includable template) implementing
`09-cicd-integration.md` §2.1:

- Stage `security`.
- `before_script`:
  - Run `pyreach sync-osv` only if the DB is missing.
  - `pip install pyreach==$PYREACH_VERSION`.
- `script`: run `pyreach` with `--manifest`, `--db-path`, `--output`, `--format sarif`,
  `--include-potentially`, `--verbose`.
- `artifacts.reports.dependency_scanning` pointing at the SARIF file; `when: always`.
- `allow_failure: false`; tags `lidercom-local-runner`, `security`.
- Document the emergency override using `--no-fail` via a manual variable
  (`pyreach_scan_override`), per `09-...md` §2.3.

### 6.2 Author the Jenkins stage template (1.5 h)

Create `ci/jenkins/Jenkinsfile.pyreach` with a declarative `Security Scan` stage:

- `agent { label 'lidercom-local-runner' }`.
- Sync DB if absent, then run `pyreach`.
- `post { always { archiveArtifacts ...; recordIssues tool: sarif(...) } }` via the Warnings
  Next Generation plugin.

### 6.3 Author the OSV sync cron job template (1 h)

Create `ci/scripts/sync-pyreach-osv.sh` from `09-...md` §3.1:

- Weekly cron script logging to `/var/log/pyreach-sync.log`.
- Exit-code handling and log rotation note.
- Document file ownership (`pyreach:pyreach`, read-only for CI).

### 6.4 Add a Dockerfile for the runner (1 h)

Create `ci/docker/Dockerfile.pyreach`:

- From `python:3.10-slim`; install the wheel; copy a pre-seeded `osv.db`; `ENTRYPOINT ["pyreach"]`.
- Document the volume mount override for the DB.

### 6.5 Wire an example into the repo and validate locally (0.5 h)

- Add `ci/examples/.gitlab-ci.yml` that `include`s the template and runs against a synthetic
  project in the repo.
- Validate that the exit-code gate blocks when SARIF contains `error` results (simulate with
  the `linear_reachable` fixture).

## Deliverables

- `ci/gitlab/.pyreach-scan.yml`
- `ci/jenkins/Jenkinsfile.pyreach`
- `ci/scripts/sync-pyreach-osv.sh`
- `ci/docker/Dockerfile.pyreach`
- `ci/examples/.gitlab-ci.yml`
- `ci/README.md` describing usage and variables.

## Acceptance Criteria

- Example `.gitlab-ci.yml` snippet runs pyreach and gates on exit code. ✅ (roadmap S4-T6)
- SARIF artifact is referenced under `reports.dependency_scanning`.
- Cron and Docker templates are complete and documented.

## Verification

- Lint YAML (`python -c "import yaml,sys; yaml.safe_load(open('ci/gitlab/.pyreach-scan.yml'))"`).
- Dry-run the Dockerfile if Docker is available.
- Document how to test without Lidercom access (use the containerized replica, R4).

## Edge Cases & Pitfalls

- GitLab `coverage`/SARIF ingestion requires GitLab Ultimate for the Security dashboard;
  document the fallback of artifact download for lower tiers.
- The `dependency_scanning` report key expects a **dependency scanning** SARIF shape; if GitLab
  rejects it, fall back to a generic `artifacts.paths` upload and document the limitation.
- Shell scripts must be POSIX (`sh`, not `bash`) where the image lacks bash.
- Quote `$PYREACH_DB_PATH` to survive spaces and unset values.

## Risks / Scope Cuts

- **R3**: if SARIF ingestion by GitLab fails, keep the artifact and gate on exit code (the gate
  is the primary value; dashboard ingestion is secondary).
- **R4**: templates must be validated against the Docker replica if Lidercom access is delayed.

## Definition of Done

- [ ] GitLab + Jenkins + cron + Docker templates merged.
- [ ] `ci/README.md` explains variable setup and override procedure.
- [ ] YAML validated; example include present.
- [ ] Gate behavior demonstrated on a synthetic project.
