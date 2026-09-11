# S4-T3 — Implement CLI argument parsing, config loading, and execution orchestration

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 8 h |
| Dependencies | S1-T2/T3, S2-*, S3-T5/T7, S4-T1/T2, S4-T5 (config module) |
| Related docs | `03-technical-specifications.md` §4; `07-sarif-and-cli-design.md` §2; `02-system-architecture.md` §Data Flow Pipeline |

## Purpose

Wire every module into a single user-facing command that runs the full pipeline and produces
output. This is the deliverable that makes PyReach usable and CI-integrable.

## Preconditions

- All analysis modules merged.
- `argparse` (stdlib) chosen; no Click dependency (`03-...md` §Technology Stack).
- `pyproject.toml` has `[project.scripts] pyreach = "pyreach.cli:main"`.

## Essential Sub-tasks

### 3.1 Implement the argument parser (2 h)

In `pyreach/cli.py`, implement exactly the options from `03-...md` §4:

```
PROJECT_PATH (positional)
-m/--manifest, -d/--db-path, -o/--output, -e/--entry-point (repeatable),
-k/--max-depth (int, default 5), --include-potentially, --include-all,
--no-fail, -f/--format {sarif,json,text}, -v/--verbose, -q/--quiet,
--version, --cache, --exclude (repeatable)
```

- Use `argparse.ArgumentParser(prog="pyreach", description=...)` with a comprehensive
  `--help` epilog containing examples from `07-...md` §2.
- `--version` reads the installed version via `importlib.metadata.version("pyreach")`.
- Validate: `max_depth >= 0`, `format` in choices, `PROJECT_PATH` exists and is a directory
  (raise `ConfigError` -> exit 2 otherwise).

### 3.2 Implement the pipeline orchestrator (2.5 h)

```python
def run_scan(args: Namespace) -> IntEnum:
    ...
```

Steps (spec `02-...md` §Data Flow):

1. Resolve configuration (S4-T5) and merge with CLI flags.
2. Parse manifest -> `list[Dependency]`.
3. Open/validate OSV DB; select advisories by package + version (S1-T5/S2-T3).
4. Build `ModuleIndex` from application sources (S2).
5. Resolve installed packages and build call graph from app + vulnerable library modules
   (S3-T3/T4).
6. Detect/resolve entry points (S3-T7); fail with `ConfigError` if empty.
7. Analyze reachability + classify (S3-T5/T6).
8. Serialize output (S4-T2) or text/JSON formatter.
9. Compute exit code (S4-T4) and return it.

- Expose the pipeline steps as small functions to keep them unit-testable.
- Log progress at INFO (`[1/4] Parsing manifest...`) unless `--quiet`.

### 3.3 Implement output format dispatch (1.5 h)

- `sarif` -> `SarifBuilder`.
- `json` -> non-SARIF machine format from `07-...md` §2.4.
- `text` -> human-readable summary from `07-...md` §2.4 (counts, reachable list, paths).
- Write to `args.output`; for `text`, print to stdout (and optionally also write if `-o`).

### 3.4 Implement progress reporting (1 h)

- Simple stage counter; suppress when `--quiet` or when stdout is not a TTY
  (`sys.stdout.isatty()`), per `07-...md` §2.6.
- Never print progress to stdout when the format is machine-readable; use stderr for progress.

### 3.5 Wire packaging / entry point (0.5 h)

- Confirm `pyreach = "pyreach.cli:main"` in `pyproject.toml`.
- `main(argv=None) -> int` returns the exit code; `if __name__ == "__main__": raise SystemExit(main())`.
- Install with `pip install .` and run `pyreach --help` to verify.

### 3.6 Write CLI tests (0.5 h)

Create `tests/e2e/test_cli_invocations.py` using `subprocess.run` (from `08-...md` §6):

| Test | Command | Expected |
|------|---------|----------|
| `test_cli_help` | `pyreach --help` | exit 0, all options listed |
| `test_cli_version` | `pyreach --version` | exit 0, `PyReach 0.1.0` |
| `test_cli_missing_project` | `pyreach /nope` | exit 2 |
| `test_cli_missing_manifest` | `pyreach /empty` | exit 2, mentions manifest |
| `test_cli_text_format` | `-f text` on fixture | exit 0/1, summary printed |
| `test_cli_output_file` | `-o out.sarif` | file created |
| `test_cli_quiet_suppresses_progress` | `-q` | no progress lines |

Use the S3-T8 synthetic projects as scan targets.

## Deliverables

- `pyreach/cli.py`
- `tests/e2e/test_cli_invocations.py`
- Confirmed `pyproject.toml` script entry.

## Acceptance Criteria

- All options from the technical spec work; `--help` is comprehensive. ✅ (roadmap S4-T3)
- CLI installable and runs on Python 3.10+ (Sprint 4 DoD).
- Pipeline orchestration is decomposed into testable steps.

## Verification

```bash
uv sync
uv run pyreach --help
uv run pyreach tests/fixtures/projects/linear_reachable -f text
uv run pytest tests/e2e -q
```

## Edge Cases & Pitfalls

- Positional `PROJECT_PATH` must still be accepted when `--version` is given (some users run
  `pyreach --version`); `--version` should short-circuit before validation.
- `Path.resolve()` the project path once; all relative outputs derive from it.
- Do not let a single unreadable file abort the scan (spec §8).
- On Windows, console encoding may mangle Unicode in text output; use plain ASCII markers.

## Risks / Scope Cuts

- **R4 (Lidercom access)**: CLI must work fully on the containerized replicas.
- If `--cache` complexity overruns, make it a no-op flag backed by the default in-memory
  build and document the deferral.

## Definition of Done

- [ ] CLI merged and installable.
- [ ] `--help` documents every option.
- [ ] E2E tests green.
- [ ] Pipeline steps unit-tested.
