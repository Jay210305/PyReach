# CI delivery and limits

The GitHub workflow runs offline tests, lint, typing, Bandit, packaging and synthetic
end-to-end validation on Python 3.10 and 3.14. Dependency acquisition during setup is
separate from analysis: the scanner never downloads source or advisories during a scan.

## GitLab / Jenkins

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

## Offline sync and containers

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

## Catálogo SQLite montado como sólo lectura

Para un montaje del archivo individual en un contenedor, publicar una copia consistente
con `PRAGMA journal_mode=DELETE` después de respaldar y antes de montarla como lectura.
Una base persistida en WAL puede requerir archivos `-wal`/`-shm`; montar sólo `osv.db`
como lectura no garantiza que SQLite pueda abrirla. No usar `immutable=1` sobre una base
viva que pueda cambiar. La sincronización trabaja sobre una copia nueva y el piloto
cambia a la instantánea validada. El ensayo de contenedor usa esta publicación.
