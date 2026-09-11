# S4-T7 — Deploy to Lidercom local runner and validate performance (<45s)

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 6 h |
| Dependencies | S4-T2, S4-T3, S4-T4, S4-T6; external Lidercom access |
| Related docs | `09-cicd-integration.md` §1, §3, §5; `10-risk-and-contingency-plan.md` §2 R4, §4 |

## Purpose

Validate PyReach in the real target environment: install on the Lidercom local runner, scan
their largest microservice, and prove the <45s performance budget and CI gating. This is the
business acceptance test.

## Preconditions

- Lidercom VPN/repository access granted (R4).
- Network access to the Lidercom runner.
- Pre-seeded OSV DB at `/opt/pyreach/osv.db`.
- CI templates merged (S4-T6).

## Essential Sub-tasks

### 7.1 Prepare the deployment package (1 h)

- Build a distributable: `uv build` (wheel + sdist) or `pip install .`.
- Publish to a location the runner can reach (internal PyPI, artifact store, or Git tag).
- Pin `PYREACH_VERSION` in the CI variables.
- Confirm the OSV DB exists and is <7 days old (`09-...md` §5).

### 7.2 Install on the runner and smoke-test (1.5 h)

- Install PyReach on the runner (or use the Docker image from S4-T6).
- Run `pyreach --version`, `pyreach --help`.
- Run a scan on a small Lidercom repo first to validate the environment before the big one.
- Capture logs; confirm no network egress during the scan (`unshare -n` / `firejail` check from
  `09-...md` §7).

### 7.3 Benchmark the largest microservice (2 h)

- Scan Lidercom's largest microservice with production settings.
- Measure wall-clock time; target **<45s**.
- Record: package count, graph node/edge counts, advisories matched, results by status,
  SARIF size, peak memory (`/usr/bin/time -v` or `tracemalloc`).
- If >45s:
  1. Retry with `--max-depth 3` (per `09-...md` §5).
  2. If still slow, retry with `--exclude tests/` and consider R1 lazy loading.
  3. Profile the hotspot and document findings.

### 7.4 Validate SARIF acceptance in the CI dashboard (1 h)

- Run the security stage end to end on a merge request.
- Confirm the SARIF artifact appears in the GitLab Security dashboard (or that the job gates
  correctly on exit code if the dashboard tier is unavailable).
- Verify `error` results annotate the MR diff where paths match changed files.

### 7.5 Document results and any deviations (0.5 h)

- Create `documentation/validation/lidercom-results.md` with the raw measurements, dates,
  repository name (or alias if confidential), and screenshots/links.
- Note any false positives/negatives and file them as issues.
- Record the R4 status (access granted/denied) and the fallback used if denied.

## Deliverables

- Deployment package (wheel/sdist or image).
- `documentation/validation/lidercom-results.md` with benchmark evidence.
- CI run link showing the security gate.
- Any filed issues for observed inaccuracies.

## Acceptance Criteria

- Scans Lidercom's largest microservice in <45 seconds. ✅ (roadmap S4-T7)
- SARIF accepted by the GitLab CI security dashboard (tested on Lidercom runner). ✅ (Sprint 4 DoD)
- No network egress during the scan (data sovereignty).

## Verification

- Re-run the benchmark twice and report p50/p95.
- Confirm the CI job blocks a merge when a reachable CVE is present (test branch).
- Confirm the emergency `--no-fail` override produces a SARIF artifact without blocking.

## Edge Cases & Pitfalls

- **R4 contingency**: if access is delayed/unavailable, run the identical protocol against the
  Docker replica in `tests/fixtures/projects/` and publicly available analogous projects, and
  document the substitution transparently (`10-...md` §2 R4).
- Runner clock/timezone affects `published_date` filters; use UTC.
- Python version on the runner may differ from dev; pin and test 3.10 specifically.
- Large dependencies may push memory >2GB; monitor and apply R1 mitigations.
- Confidential code must not leave Lidercom's environment; store only aggregate metrics.

## Risks / Scope Cuts

- **R4 (access delay)**: containerized replica is the standing fallback.
- **R1 (performance)**: reducing `--max-depth` to 3 is the sanctioned fallback; document the
  precision trade-off.

## Definition of Done

- [ ] PyReach installed and working on the Lidercom runner (or documented replica).
- [ ] <45s benchmark recorded with evidence.
- [ ] SARIF accepted by the dashboard (or artifact fallback documented).
- [ ] Validation report committed.
