# S4-T4 — Implement exit code logic and error handling hierarchy

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 4 h |
| Dependencies | S4-T3, `exceptions.py` (S1-T1) |
| Related docs | `03-technical-specifications.md` §4 (exit codes), §8 (errors); `09-cicd-integration.md` §2.3, §8 |

## Purpose

Exit codes are the CI quality gate: they decide whether a pipeline blocks a deployment. They
must be correct, documented, and covered by integration tests.

## Preconditions

- CLI orchestrator exists (S4-T3).
- Exception hierarchy defined (`PyReachError` and subclasses).

## Essential Sub-tasks

### 4.1 Finalize the exception hierarchy (1 h)

In `pyreach/exceptions.py`, complete spec §8:

```
PyReachError
├── ConfigError
├── ParseError
├── OSVError
├── AnalysisError
└── OutputError
```

- Each carries a user-facing message; no stack traces leak to stdout by default.
- Map internal exceptions to these at module boundaries.

### 4.2 Implement the exit code resolver (1.5 h)

```python
class ExitCode(IntEnum):
    SUCCESS = 0
    FINDINGS = 1
    ERROR = 2

def compute_exit_code(results, args: Namespace) -> ExitCode:
    ...
```

Rules (`03-...md` §4, `09-...md` §2.3):

| Condition | Code |
|-----------|------|
| `--no-fail` | 0 (regardless of findings) |
| Any `REACHABLE` | 1 |
| Any `POTENTIALLY_REACHABLE` **and** `--include-potentially` | 1 |
| Only `NOT_REACHABLE` (or none) | 0 |
| `ConfigError`/`ParseError`/`OSVError`/`AnalysisError`/`OutputError` | 2 |

- Order matters: error handling wraps the whole `run_scan`, returning 2 on any caught
  `PyReachError`; unexpected exceptions also map to 2 with a logged traceback at DEBUG.

### 4.3 Implement top-level error handling (1 h)

- `main()` catches `PyReachError` -> log ERROR message, return 2.
- Catch `KeyboardInterrupt` -> return 2 (or 130 as a courtesy; document).
- Catch `MemoryError` -> friendly message advising `--max-depth`/`--exclude` (spec §8).
- `--verbose` includes exception chain; default hides tracebacks.

### 4.4 Implement error messages per the UX table (0.5 h)

Reuse the messages from `07-...md` §3:

- Missing manifest -> `ConfigError("Manifest file 'x' not found...")`.
- Missing OSV DB -> `OSVError("OSV database not found at ... Run 'pyreach sync-osv'.")`.
- No entry points -> `ConfigError("No entry points detected. Use -e ...")`.
- Syntax error -> WARNING only (never exit 2).
- Memory -> `AnalysisError("Memory limit exceeded...")`.

### 4.5 Write tests (1 h)

Create `tests/unit/test_exit_codes.py` and extend `tests/e2e/test_cli_invocations.py`:

| Test | Setup | Expected |
|------|-------|----------|
| `test_no_findings_exit_zero` | clean project | 0 |
| `test_reachable_exit_one` | vulnerable project | 1 |
| `test_potential_only_exit_zero_by_default` | potential only | 0 |
| `test_include_potentially_exit_one` | potential + flag | 1 |
| `test_no_fail_overrides_findings` | reachable + `--no-fail` | 0 |
| `test_missing_manifest_exit_two` | empty dir | 2 |
| `test_missing_db_exit_two` | bad `-d` | 2 |
| `test_no_entry_points_exit_two` | undetectable project | 2 |
| `test_memory_error_exit_two` | monkeypatched `MemoryError` | 2 |
| `test_unexpected_exception_exit_two` | monkeypatched runtime error | 2 |

- E2E asserts actual process exit codes via `subprocess.run(...).returncode`.

## Deliverables

- `pyreach/exceptions.py` (completed hierarchy).
- `ExitCode` + `compute_exit_code` in `pyreach/cli.py` (or `pyreach/exit_codes.py`).
- `tests/unit/test_exit_codes.py`, extended e2e tests.

## Acceptance Criteria

- Exit codes 0/1/2 behave as specified; integration tests verify. ✅ (roadmap S4-T4)
- `--no-fail` and `--include-potentially` interact correctly.
- Errors never produce a raw traceback unless `--verbose`.

## Verification

```bash
poetry run pytest tests/unit/test_exit_codes.py tests/e2e -q
poetry run pyreach tests/fixtures/projects/linear_reachable; echo $LASTEXITCODE
poetry run pyreach tests/fixtures/projects/linear_reachable --no-fail; echo $LASTEXITCODE
```

## Edge Cases & Pitfalls

- `--no-fail` must not suppress error code 2; it only affects findings.
- `--include-potentially` plus `--no-fail`: `--no-fail` wins -> 0.
- A `ParseError` on one file is downgraded to a warning and must **not** yield 2.
- On Windows PowerShell, `$LASTEXITCODE`/`$?` semantics differ; e2e tests should use Python's
  `subprocess.returncode`.

## Risks / Scope Cuts

- None; CI gating depends on this. Do not cut.

## Definition of Done

- [ ] Exit code logic merged and tested.
- [ ] Error messages match the UX table.
- [ ] E2E asserts process exit codes.
- [ ] No traceback leakage by default.
