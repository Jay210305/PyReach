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

## CI delivery and limits

The GitHub workflow runs offline tests, lint, typing, Bandit, packaging and synthetic
end-to-end validation on Python 3.10 and 3.14. Dependency acquisition during setup is
separate from analysis: the scanner never downloads source or advisories during a scan.

### GitLab / Jenkins

Install the approved wheel in the runner, and seed a local DB beforehand:

```sh
pyreach sync-osv --source /approved/osv-jsonl --db-path /opt/pyreach/osv.db
```

Include `ci/gitlab/.pyreach-scan.yml` and extend `.pyreach-scan`; declare `security`
in your pipeline stages. The template blocks on exit 1 or 2 and retains SARIF even
when blocked. It uses generic artifacts, so it works without a Security dashboard.
Use a protected runner and read-only DB for scans. `PYREACH_DB_PATH` and
`PYREACH_MANIFEST` are explicit job variables. Emergency bypass requires an authorized,
logged change to `--no-fail`; do not silently disable a blocking job.

Do **not** label SARIF as `reports.dependency_scanning`: that key has a different schema.
On GitLab Ultimate with native SARIF ingestion enabled, use the optional
`ci/gitlab/sarif-dashboard.yml`, declaring stages `security` and `gate`. The report
producer returns success for ingestion, but propagates operational errors; the separate
gate consumes the captured exit code. Findings without a physical location remain
valid SARIF but may not be displayed by GitLab. Validate the actual server version
before adoption: https://docs.gitlab.com/user/application_security/detect/sarif/.
No dashboard acceptance or Lidercom deployment is claimed by this repository.

The Jenkins example needs the labeled runner and pre-installed wheel. It gates on
the CLI exit status and always archives SARIF. Enable a SARIF visualization plugin
only after validating compatibility in the target Jenkins installation.

### Offline sync and containers

`ci/scripts/sync-pyreach-osv.sh` is a POSIX weekly-job entry point; schedule it from
an administrator-owned cron, e.g. `0 2 * * 0`, with `PYREACH_OSV_SOURCE` pointing to
approved local data. Rotate scheduler logs and own the DB as `pyreach:pyreach`;
CI readers should not modify it. Downloads, if required, are a separate approved step.

```sh
uv build
# Build with network only to acquire runtime wheels; the scan itself stays offline.
docker build -f ci/docker/Dockerfile.pyreach -t pyreach:0.1.0 .
docker run --rm --network none -v "$PWD:/work:ro" -v "$PWD/out:/out" \
  -v /approved/osv.db:/data/osv.db:ro pyreach:0.1.0 \
  /work -d /data/osv.db -o /out/results.sarif
```

The image is non-root. Keep build artifacts and deployment credentials outside the
source image. Verify the wheel digest, keep the prior wheel/DB for rollback, and
replay `scripts/validate_release.py` before enabling a gate on real projects.

### Catálogo SQLite montado como sólo lectura

Para un montaje del archivo individual en un contenedor, publicar una copia consistente
con `PRAGMA journal_mode=DELETE` después de respaldar y antes de montarla como lectura.
Una base persistida en WAL puede requerir archivos `-wal`/`-shm`; montar sólo `osv.db`
como lectura no garantiza que SQLite pueda abrirla. No usar `immutable=1` sobre una base
viva que pueda cambiar. La sincronización trabaja sobre una copia nueva y el piloto
cambia a la instantánea validada. El ensayo de contenedor usa esta publicación.
