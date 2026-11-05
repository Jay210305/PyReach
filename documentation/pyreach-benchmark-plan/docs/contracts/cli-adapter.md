# Contract C-CLI 1.0.0 — PyReach subprocess adapter

## Interface and provenance
Public owner-provided entry point; verify under S0-T1. Existing CLI (not an assumed programmatic Python import):
```bash
uv run --offline --no-sync pyreach /absolute/path/to/project --db-path /absolute/path/osv.db -o /absolute/path/result.sarif
```
**Inputs:** POSIX/Windows resolved absolute paths, pinned project/source SHA, existing SQLite OSV DB, 120s/900s timeout, frozen environment; optional `-f text`, `--no-fail` only after help confirms semantics. **Output:** process `returncode:int`, stdout/stderr as UTF-8 replacement decode, output SARIF file when `-o`, timing and peak RSS. **Exit:** 0 clean / no-fail, 1 reachable finding, 2 configuration/runtime error. Exit 1 is *successfully executed scanner with a finding*, not harness error. **Side effects:** creates only specified output and bounded tmp files; scanner must not write to third-party source.

## Harness API to implement
```python
def scan_case(project: Path, db: Path, sarif_out: Path, timeout_s: int) -> ProcessObservation: ...
```
`ProcessObservation` fields: `argv: list[str]`, `exit_code: int | None`, `stdout: str`, `stderr: str`, `sarif_path: str | None`, `duration_s: float`, `peak_rss_kib: int | None`, `error_code: str | None`. Invalid input raises `ValueError` before execution and reports `SCHEMA_INVALID`; process crash/error `CLI_ERROR`; timeout `TIMEOUT`. Unknown undocumented exit code → `UNKNOWN_TOOL_OUTPUT`.

## Valid example
Input paths exist, `argv=["uv","run","--offline","--no-sync","pyreach","/tmp/app","--db-path","/tmp/db.sqlite","-o","/tmp/out.sarif"]`; return 1 with valid SARIF reachability findings → harness `run_status=completed`, `scanner_exit_code=1`.

## Invalid example
`db="/missing/osv.db"` → either reject preflight with `SCHEMA_INVALID` or observe CLI error `2`, preserving distinction; **never classify as 'clean'**.

## Contract tests first
1. Pass subprocess fake output/exit 1, assert completed not error.
2. Exit 0/1/2 with dummy paths; assert correct classification; one malformed SARIF triggers schema gate failure.
3. Offline case exercised with Linux network isolation; if denied enforcement impossible, mark blocked and do not claim offline.
