# S1-T5 — Implement `OSVImporter` with JSONL streaming

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 10 h |
| Dependencies | S1-T4 (schema + connection) |
| Related docs | `03-technical-specifications.md` §6; `05-data-model-and-storage.md` §OSV Ingestion Algorithm, §Version Range Handling; `02-system-architecture.md` §OSV Mapper |

## Purpose

Populate the local SQLite advisory database from an OSV JSONL dump without loading it into
memory. This is the largest Sprint 1 task and the source of all vulnerability data used by
Sprints 3-4. It must ingest 10,000+ PyPI records in under 5 minutes.

## Preconditions

- S1-T4 merged (`initialize_database`, `get_db_connection`).
- At least one sample OSV JSONL file under `tests/fixtures/osv_records/`.
- Knowledge of the OpenSSF OSV schema v1.6.0: fields `id`, `aliases`, `modified`,
  `published`, `summary`, `severity[]`, `affected[]`, `affected[].package.ecosystem`,
  `affected[].ranges[]`, `affected[].versions[]`, `affected[].ecosystem_specific`.

## Essential Sub-tasks

### 5.1 Define OSV record parsing helpers (1.5 h)

In `pyreach/parsers/osv_json.py`:

- `parse_osv_record(record: dict) -> Vulnerability | None` using the `Vulnerability`
  dataclass from spec §3.4.
- Return `None` (not raise) when `affected[].package.ecosystem != "PyPI"`.
- Extract:
  - `osv_id = record["id"]`.
  - `cve_id`: first alias matching `^CVE-\d{4}-\d+$`, else `None`.
  - `severity_score` / `severity_level`: from `severity[]` CVSS vector + score; map
    `CVSS:3.1` scores -> LOW/MEDIUM/HIGH/CRITICAL via standard bands.
  - `published_date = record.get("published")` (date part only).
  - `summary = record.get("summary", "")`.
- Handle malformed records by returning `None` and counting them; never crash the stream.

### 5.2 Define the affected-range/symbol extractor (2.0 h)

Create `extract_affected(record)` returning a list of:
`(symbol_fqn, version_introduced, version_fixed)`.

- Walk `affected[]`; for each:
  - `package_name` normalized with `normalize_name`.
  - For each `ranges[]` of type `ECOSYSTEM`/`SEMVER`, walk `events[]` accumulating
    `introduced` -> `fixed` / `last_affected` pairs.
  - Symbols come from `ecosystem_specific.imports[].symbols` when present (this is the key
    PyPI-specific field) or from `ecosystem_specific.symbols` as a fallback.
  - If no symbols are published (common), emit a sentinel `package_name` symbol and mark it
    for conservative classification later. Document the sentinel value (e.g. `"*"`).
- `is_version_affected(version, introduced, fixed)` exactly as spec §Version Range Handling,
  using `packaging.version.Version`; guard `InvalidVersion` by returning `True` (conservative).

### 5.3 Implement milestone-based streaming reader (1.5 h)

In `pyreach/osv/importer.py`:

- `iter_osv_records(path: Path) -> Iterator[dict]`:
  - Support both **JSONL** (one JSON object per line) and a JSON array file.
  - Stream line-by-line; use `json.loads` per line for JSONL.
  - Skip blank lines and lines that fail to parse, incrementing a `skipped` counter.
- Never call `path.read_text()` on the full dump (memory risk).

### 5.4 Implement the `OSVImporter` class (2.5 h)

```python
class OSVImporter:
    def __init__(self, db_path: str | Path, incremental: bool = False) -> None: ...
    def import_file(self, path: Path) -> ImportStats: ...
```

- `ImportStats` dataclass: `total`, `imported`, `skipped_ecosystem`, `skipped_malformed`,
  `symbols_imported`, `elapsed_seconds`.
- Upsert `advisories` with `ON CONFLICT(osv_id) DO UPDATE` (see `repositories.py` pattern
  in spec §Repository Pattern); store `raw_json`.
- Replace `affected_symbols` rows for a given advisory before re-inserting (delete + insert
  inside the same transaction) so re-runs are idempotent.
- Incremental mode: read last sync from `schema_version` metadata or a dedicated
  `sync_metadata` row; skip records whose `modified` <= last sync. Update timestamp after a
  successful full pass.
- Batch commits every N records (e.g. 1000) for throughput, but the whole file is one logical
  operation; on error roll back the current batch and report.

### 5.5 Add the `pyreach sync-osv` entry hook (0.5 h)

Expose a callable `sync_osv(db_path, source, incremental)` used by the CLI subcommand
(`07-sarif-and-cli-design.md` §2.3). Accept a local directory of JSONL files in addition to a
single file. Network download is **out of scope for Sprint 1**; accept a local path and raise a
clear `OSVError` if a URL is passed (implement URL download in a later increment if time).

### 5.6 Write tests with fixtures (2.0 h)

Create `tests/unit/osv/test_importer.py` and fixtures:

| Test | Assertion |
|------|-----------|
| `test_import_single_record` | advisory + symbols rows exist |
| `test_skip_non_pypi` | npm record ignored; stats.skipped_ecosystem == 1 |
| `test_skip_malformed_line` | malformed JSONL line counted, stream continues |
| `test_idempotent_reimport` | running twice yields same row counts |
| `test_version_range_matching` | `is_version_affected` truth table |
| `test_severity_mapping` | CVSS 9.8 -> `CRITICAL`; 5.0 -> `MEDIUM` |
| `test_symbol_sentinel_when_absent` | advisory with no imports gets `*` symbol |
| `test_incremental_skips_old` | record with old `modified` not re-imported |
| `test_stats_accuracy` | counts match fixture contents |

Fixtures: hand-write 5-8 small OSV records covering PyPI, non-PyPI, malformed, aliased,
symbols-present, symbols-absent.

### 5.7 Performance smoke test (0.5 h)

Add a test (or manual script) that generates/ships a 10k-record JSONL and asserts ingestion
`< 5 min` (ideally < 30 s). Mark it `@pytest.mark.performance` so it can be skipped in fast CI.

## Deliverables

- `pyreach/parsers/osv_json.py`
- `pyreach/osv/importer.py`
- `pyreach/osv/__init__.py`
- `pyreach/db/repositories.py` (advisory upsert used by importer)
- `tests/unit/osv/test_importer.py`, `tests/unit/parsers/test_osv_json.py`
- `tests/fixtures/osv_records/*.jsonl`

## Acceptance Criteria

- Successfully ingests 10,000+ OSV PyPI records in <5 min. ✅ (roadmap S1-T5)
- Idempotent re-import; non-PyPI and malformed records handled.
- Incremental mode skips already-synced records.
- Streaming: peak memory independent of file size.

## Verification

```bash
poetry run pytest tests/unit/osv tests/unit/parsers/test_osv_json.py -q
poetry run pytest -m performance tests/unit/osv -q
python -c "from pyreach.osv.importer import OSVImporter; print(OSVImporter('C:/tmp/osv.db').import_file('tests/fixtures/osv_records/sample.jsonl'))"
```

## Edge Cases & Pitfalls

- `aliases` may be `null`; treat as `[]`.
- Multiple severity entries: prefer CVSS v3.1 then v4 then v2; if none, `severity_level=None`.
- `versions[]` (explicit list) must also be honored, not just `ranges[]`.
- `last_affected` is inclusive; `fixed` is exclusive — do not confuse them.
- Huge `raw_json` inflates DB size; consider only storing if `--store-raw` is set (document).
- Duplicate symbols across ranges must be de-duplicated per advisory.

## Risks / Scope Cuts

- **R1 (graph explosion)** is unrelated, but the same lazy philosophy applies: import only
  metadata now; symbol expansion is done at query time.
- If network download is required for the demo, implement `sync-osv --source <url>` via
  `urllib.request` with a single-file download; note data-sovereignty rules (fetch stage only).

## Definition of Done

- [ ] Importer + repo merged; 9+ tests green.
- [ ] Idempotency and incremental sync verified.
- [ ] 10k-record benchmark documented.
- [ ] `sync_osv` callable exposed for the CLI.
