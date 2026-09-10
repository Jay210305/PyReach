# CI/CD Integration

## 1. Integration Goals

PyReach must operate as a first-class citizen within Lidercom Peru S.A.C.'s existing continuous integration pipelines. The integration must:

1. **Gate deployments**: Fail the pipeline when reachable vulnerabilities are detected.
2. **Report natively**: Produce SARIF artifacts consumed by GitLab security dashboards or Jenkins plugins.
3. **Respect data sovereignty**: Execute entirely on local runners; no external API calls.
4. **Perform within limits**: Complete in <45 seconds to avoid blocking developer feedback loops.
5. **Be maintainable**: Update OSV database automatically via scheduled jobs.

## 2. CI/CD Architecture

### 2.1 GitLab CI Integration (Primary Target)

Lidercom uses GitLab with local runners. PyReach integrates as a dedicated stage.

```yaml
# .gitlab-ci.yml (to be included in target projects or as a template)

stages:
  - build
  - test
  - security
  - deploy

variables:
  PYREACH_VERSION: "0.1.0"
  PYREACH_DB_PATH: "/opt/pyreach/osv.db"

# ------------------------------------------------------------------
# Build and test stages remain unchanged
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Security Stage: PyReach Scan
# ------------------------------------------------------------------
pyreach_scan:
  stage: security
  image: python:3.10-slim
  variables:
    PYREACH_OUTPUT: "pyreach-results.sarif"
  before_script:
    # Ensure OSV DB is present on the runner (pre-seeded via cron)
    - |
      if [ ! -f "$PYREACH_DB_PATH" ]; then
        echo "OSV database missing. Running sync..."
        pyreach sync-osv --db-path "$PYREACH_DB_PATH"
      fi
    # Install PyReach
    - pip install pyreach==$PYREACH_VERSION
  script:
    - pyreach
        --manifest requirements.txt
        --db-path "$PYREACH_DB_PATH"
        --output "$PYREACH_OUTPUT"
        --format sarif
        --include-potentially
        --verbose
  artifacts:
    when: always
    paths:
      - "$PYREACH_OUTPUT"
    reports:
      # GitLab Ultimate/Security Center SARIF ingestion
      dependency_scanning:
        - "$PYREACH_OUTPUT"
  allow_failure: false
  tags:
    - lidercom-local-runner
    - security
```

### 2.2 Jenkins Integration (Alternative)

For Jenkins pipelines (Groovy declarative syntax):

```groovy
pipeline {
    agent { label 'lidercom-local-runner' }
    environment {
        PYREACH_DB = '/opt/pyreach/osv.db'
        PYREACH_OUT = 'pyreach-results.sarif'
    }
    stages {
        stage('Build') { ... }
        stage('Test') { ... }
        stage('Security Scan') {
            steps {
                sh '''
                    if [ ! -f "$PYREACH_DB" ]; then
                        pyreach sync-osv --db-path "$PYREACH_DB"
                    fi
                    pyreach \
                        --manifest requirements.txt \
                        --db-path "$PYREACH_DB" \
                        --output "$PYREACH_OUT" \
                        --format sarif \
                        --include-potentially
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: "$PYREACH_OUT", allowEmptyArchive: true
                    // Optional: publish SARIF via Jenkins Warnings Next Generation plugin
                    recordIssues enabledForFailure: true, tool: sarif(pattern: "$PYREACH_OUT")
                }
            }
        }
    }
}
```

### 2.3 Quality Gate Logic

| Exit Code | Pipeline Action | Rationale |
|-----------|-----------------|-----------|
| 0 | Continue to Deploy stage | No reachable vulnerabilities |
| 1 | Block deploy; notify team | Reachable (or potentially reachable) CVEs found |
| 2 | Block deploy; page on-call | Infrastructure / configuration error |

**Override for emergency hotfixes:**
```bash
# Manual pipeline variable
pyreach_scan_override: "true"
```
When set, the CI job runs with `--no-fail` but still generates the SARIF report for audit.

## 3. Runner Setup and Maintenance

### 3.1 Pre-Seeded OSV Database

Local runners must maintain an up-to-date OSV SQLite database without downloading it on every build.

**Weekly Sync Cron Job (on runner host):**
```bash
#!/usr/bin/env bash
# /etc/cron.weekly/sync-pyreach-osv

PYREACH_DB="/opt/pyreach/osv.db"
PYREACH_LOG="/var/log/pyreach-sync.log"

echo "[$(date -Iseconds)] Starting OSV sync..." >> "$PYREACH_LOG"
pyreach sync-osv --db-path "$PYREACH_DB" --incremental >> "$PYREACH_LOG" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -Iseconds)] OSV sync completed successfully." >> "$PYREACH_LOG"
else
    echo "[$(date -Iseconds)] OSV sync FAILED with code $EXIT_CODE." >> "$PYREACH_LOG"
    # Notify admin via existing monitoring (optional)
fi
```

**Permissions:**
- DB file owned by `pyreach:pyreach` (dedicated service group).
- CI runner process has read-only access to `/opt/pyreach/osv.db`.
- Cron job runs as `pyreach` user with write access.

### 3.2 Runner Hardware Specification

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disk | 20 GB (OS + cache) | 50 GB (multi-project cache) |
| Network | Internal only (no egress to cloud APIs during scan) | Same |

### 3.3 Docker Image (Optional Containerization)

For consistency across runners or local developer environments:

```dockerfile
# Dockerfile.pyreach
FROM python:3.10-slim

WORKDIR /opt/pyreach

# Install PyReach
COPY dist/pyreach-*.whl .
RUN pip install pyreach-*.whl

# Pre-seed OSV DB (can be overridden with volume mount)
COPY osv.db /opt/pyreach/osv.db

ENTRYPOINT ["pyreach"]
```

```yaml
# GitLab CI using custom image
pyreach_scan:
  stage: security
  image: lidercom.local:5000/pyreach:0.1.0
  script:
    - pyreach --db-path /opt/pyreach/osv.db --output pyreach-results.sarif .
```

## 4. SARIF Dashboard Integration

### 4.1 GitLab Security Dashboard

GitLab Ultimate ingests SARIF `dependency_scanning` reports and displays:
- Vulnerability list with severity.
- Code flow visualization (if viewer supports `codeFlows`).
- Merge request diff annotations (if path matches changed files).

**Required SARIF mappings for GitLab:**
- `result.ruleId` -> Vulnerability identifier.
- `result.level` -> Severity mapping:
  - `error` -> Critical/High
  - `warning` -> Medium
  - `note` -> Low / Ignored
- `result.locations[].physicalLocation.artifactLocation.uri` -> File path in repository.

### 4.2 VS Code SARIF Viewer (Developer Local)

Developers can open `pyreach-results.sarif` locally:

```bash
# After local scan
code pyreach-results.sarif
```

The Microsoft SARIF Viewer extension renders:
- Result list with reachability status badges.
- Call path navigation through `codeFlows`.
- Direct links to source locations.

## 5. Performance Budget in CI

| Metric | Budget | Monitoring |
|--------|--------|------------|
| Scan duration | <45s | CI job timer; alert if p95 >40s |
| SARIF file size | <5 MB | Artifact size check |
| Memory consumption | <2 GB | Runner cgroup limits |
| OSV DB age | <7 days | Cron job log monitoring |

**Performance regression procedure:**
1. If scan exceeds 45s: Automatically retry once with `--max-depth 3`.
2. If still exceeding: Fail with diagnostic output (`--verbose`) for profiling.
3. Monthly review of p50/p95 scan times to detect gradual degradation.

## 6. Rollback and Compatibility

### Version Pinning
Projects pin PyReach version in CI variables:
```yaml
variables:
  PYREACH_VERSION: "0.1.0"
```

### Backward Compatibility
- SARIF schema version locked to 2.1.0.
- CLI options deprecated for 2 minor versions before removal.
- Database schema migrated automatically on first run of newer version.

## 7. Audit and Compliance

### Data Sovereignty Verification

To demonstrate zero cloud egress during scans:

```bash
# Pre-scan: verify no network namespaces are used
unshare -n pyreach /path/to/project  # Should still work (local DB only)

# Or using firejail
firejail --net=none pyreach /path/to/project
```

This proves PyReach does not require network connectivity during analysis.

### Audit Trail

CI pipelines should retain SARIF artifacts for compliance reviews:
- Retention period: 1 year (aligned with ISO/IEC 27001 audit cycles).
- Naming convention: `pyreach-results-<PROJECT>-<BRANCH>-<COMMIT_SHA>.sarif`.

## 8. Troubleshooting Guide for CI Operators

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `Exit 2: OSV database not found` | First run or DB deleted | Run `pyreach sync-osv` on runner host |
| `Exit 2: No entry points detected` | Project lacks obvious `main` or framework decorators | Add `-e` flags to CI job or `.pyreach.yml` to project repo |
| Scan >45s consistently | Large dependency tree or deep call graph | Increase runner RAM; reduce `--max-depth`; exclude test directories |
| SARIF not appearing in GitLab Security tab | Wrong `artifacts.reports` key or invalid SARIF | Validate SARIF with `jsonschema` locally; check GitLab version supports SARIF |
| False positive flood | Conservative heuristic too aggressive | Review `.pyreach.yml` ignore patterns; tune `--include-potentially` flag |

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
