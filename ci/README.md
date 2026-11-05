# PyReach CI/CD Templates (S4-T6)

Copy-paste-ready pipeline templates that run PyReach as a security quality
gate and publish SARIF. Primary target: Lidercom GitLab with local runners
(doc `09-cicd-integration.md`); Jenkins provided as alternative.

## Contents

| File | Purpose |
|------|---------|
| `gitlab/.pyreach-scan.yml` | Includable GitLab template (hidden job `.pyreach-scan`) |
| `jenkins/Jenkinsfile.pyreach` | Declarative Jenkins pipeline with a `Security Scan` stage |
| `scripts/sync-pyreach-osv.sh` | Weekly OSV DB sync cron script (POSIX `sh`) |
| `docker/Dockerfile.pyreach` | Runner image; DB provided via read-only volume mount (R4 replica) |
| `examples/.gitlab-ci.yml` | Consumer example gating on the `linear_reachable` fixture |

## Variables (GitLab template)

| Variable | Default | Description |
|----------|---------|-------------|
| `PYREACH_VERSION` | `0.1.0` | Release label for the runner image |
| `PYREACH_DB_PATH` | `/opt/pyreach/osv.db` | Pre-seeded OSV SQLite database (always quote) |
| `PYREACH_MANIFEST` | `requirements.txt` | Manifest relative to the project path |
| `PYREACH_PROJECT_PATH` | `.` | Scanned project root |
| `PYREACH_OUTPUT` | `pyreach-results.sarif` | SARIF artifact path |
| `PYREACH_MAX_DEPTH` | `5` | Traversal depth (never > 7) |
| `PYREACH_EXTRA_ARGS` | `""` | Extra flags, e.g. `-e myapp.main --exclude tests/` |
| `PYREACH_SCAN_OVERRIDE` | `"false"` | Emergency override (see below) |

## Quality gate

Exit codes drive the gate (`allow_failure: false`):

| Code | Meaning | Pipeline |
|------|---------|----------|
| 0 | No reachable findings (or override) | Continues |
| 1 | Reachable (or `--include-potentially`) findings | Blocked, team notified |
| 2 | Config/runtime error | Blocked, on-call paged |

The scan job publishes `artifacts.reports.sarif` and succeeds on finding exit
code 1 so GitLab can ingest the report. A separate `pyreach_gate` job reads
`pyreach-exit-code.txt` and blocks the pipeline. Exit code 2 fails the scan
job directly. The fixed PyReach rule IDs are reported as SARIF findings;
GitLab does not classify them as native dependency-scanning vulnerabilities.

## Emergency override

For hotfixes, run a manual pipeline with `PYREACH_SCAN_OVERRIDE=true`
(GitLab) or `PYREACH_SCAN_OVERRIDE=true` build parameter (Jenkins). The job
adds `--no-fail` (exit 0) but still archives SARIF for audit.

## OSV database maintenance

1. Create the service account: DB file owned `pyreach:pyreach`, mode `0640`
   (CI runner reads via group).
2. Install the cron job as the `pyreach` user:
   `0 3 * * 0 pyreach /opt/pyreach/bin/sync-pyreach-osv.sh`
3. Set `PYREACH_OSV_SOURCE` to a local mirrored OSV archive; override paths via
   `PYREACH_DB_PATH` / `PYREACH_SYNC_LOG` env vars.
4. Log rotation (`/etc/logrotate.d/pyreach`):
   ```
   /var/log/pyreach-sync.log {
       weekly
       rotate 8
       compress
       missingok
       notifempty
   }
   ```

## Prerequisites

- Build and publish `pyreach:0.1.0` from `ci/docker/Dockerfile.pyreach` to a
  registry the runner can access. Mount the pre-seeded DB read-only at
  `PYREACH_DB_PATH` in both scan and gate jobs.
- The consuming pipeline defines `security` and `security_gate` stages and
  jobs extending `.pyreach-scan` and `.pyreach-gate` (see `examples/`).
- GitLab runner tagged `lidercom-local-runner` (+ `security`), or the Docker
  replica below (R4).

## Testing without Lidercom access (R4)

```powershell
# Gate blocks on reachable findings (exit 1 + error-level SARIF result)
uv run pytest tests/unit/test_ci_templates.py -q
# Manual replica of the CI scan step (no install needed):
uv run python -m pyreach.cli tests/fixtures/projects/linear_reachable `
  --db-path <seeded-osv.db> --format sarif --include-potentially `
  --output pyreach-results.sarif
# Docker replica (wheel built via `uv build`; DB is a volume mount):
# docker build -f ci/docker/Dockerfile.pyreach -t pyreach:0.1.0 .
# docker run --rm -v /opt/pyreach/osv.db:/opt/pyreach/osv.db:ro \
#   -v "$PWD:/work:ro" pyreach:0.1.0 /work --db-path /opt/pyreach/osv.db
```

Performance budget in CI: scan < 45 s, SARIF < 5 MB, runner < 2 GB RAM,
DB age < 7 days (doc 09 §5).
