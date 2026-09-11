# S1-T4 — Design SQLite schema

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 4 h |
| Dependencies | S1-T1 |
| Related docs | `05-data-model-and-storage.md` (authoritative DDL); `02-system-architecture.md` §Internal Store |

## Purpose

Create the DDL and connection layer that backs OSV ingestion, optional call-graph caching,
and reachability memoization. The schema is the integration point between Sprint 1 (writes
advisories) and Sprints 3-4 (reads them). It must be 3NF and indexed for read-heavy analysis.

## Preconditions

- Python's `sqlite3` available (stdlib).
- `05-data-model-and-storage.md` §Schema Definition reviewed (it is the source DDL).

## Essential Sub-tasks

### 4.1 Create `pyreach/db/schema.sql` from the spec (1.0 h)

Copy the DDL verbatim from `05-data-model-and-storage.md` §Schema Definition. Required tables:

| Table | Purpose |
|-------|---------|
| `advisories` | OSV records keyed by `osv_id` (UNIQUE) |
| `affected_symbols` | symbol FQNs per advisory; FK -> advisories |
| `cg_nodes` | optional call-graph node cache |
| `cg_edges` | optional call-graph edge cache; FKs -> cg_nodes |
| `reachability_results` | memoized classifications |
| `file_hashes` | SHA256 change detection for caching |
| `schema_version` | integer migration tracking |

Requirements:
- Every `CREATE` uses `IF NOT EXISTS`.
- Foreign keys include `ON DELETE CASCADE` where specified.
- All indexes from the spec are present (`idx_advisories_package`, `idx_affected_symbols_fqn`,
  `idx_cg_nodes_fqn`, `idx_reachability_symbol`, ...).
- Insert initial `schema_version` value `1`.

### 4.2 Implement `pyreach/db/connection.py` (1.5 h)

- `get_db_connection(db_path)` context manager exactly as spec §Data Access Layer:
  - `sqlite3.connect(str(db_path), check_same_thread=False)`.
  - `row_factory = sqlite3.Row`.
  - `PRAGMA foreign_keys = ON`.
  - commit on success, rollback + raise `DatabaseError` on failure, close in `finally`.
- Add `initialize_database(db_path)`: reads `schema.sql` via `importlib.resources`, executes
  `executescript`, and verifies `schema_version`.
- Add `get_schema_version(conn) -> int`.
- Use `pathlib.Path`; create parent directory for `~/.pyreach/osv.db` if missing.

### 4.3 Enforce 3NF and document normalization (0.5 h)

- Confirm no transitive dependencies on non-key attributes:
  - advisory facts only in `advisories`; symbol facts only in `affected_symbols`.
  - `raw_json` is stored for audit but is not used for querying (document this).
- Add a short comment header in `schema.sql` describing each table and its normal form.

### 4.4 Write schema tests (1.0 h)

Create `tests/unit/db/test_schema.py`:

| Test | Assertion |
|------|-----------|
| `test_initialize_creates_all_tables` | query `sqlite_master` for all 7 tables |
| `test_foreign_keys_enabled` | `PRAGMA foreign_keys` returns 1 |
| `test_unique_osv_id` | duplicate insert raises `IntegrityError` |
| `test_cascade_delete` | deleting advisory deletes its symbols |
| `test_indexes_exist` | all expected index names present |
| `test_schema_version_is_one` | `get_schema_version == 1` |
| `test_connection_rollback_on_error` | failing statement leaves DB unchanged |
| `test_initialize_idempotent` | running twice does not error |

Use an in-memory or `tmp_path` SQLite file.

## Deliverables

- `pyreach/db/schema.sql`
- `pyreach/db/connection.py`
- `pyreach/db/__init__.py`
- `tests/unit/db/test_schema.py`
- `pyreach/db/migrations/` directory (empty or with a README placeholder)

## Acceptance Criteria

- Schema reviewed; 3NF compliance check. ✅ (roadmap S1-T4)
- All 7 tables + all indexes created by a single `initialize_database()` call.
- Connection manager commits on success and rolls back on error.
- Tests green.

## Verification

```bash
uv run pytest tests/unit/db/test_schema.py -q
python -c "from pyreach.db.connection import initialize_database; initialize_database('C:/tmp/test.db')"
sqlite3 C:/tmp/test.db ".schema"
```

## Edge Cases & Pitfalls

- `PRAGMA foreign_keys` is per-connection; it MUST be set on every connection, not once.
- `executescript` implicitly commits any pending transaction — call it only during init.
- Windows paths with backslashes must be passed through `Path` before string conversion.
- `check_same_thread=False` is needed because tests may share a connection; document the
  threading assumption (analysis is single-threaded unless `pytest-xdist`).

## Risks / Scope Cuts

- Call-graph caching tables (`cg_nodes`, `cg_edges`) may remain unused until Sprint 3. Keeping
  them in the schema now avoids a migration later; do not drop them.
- If time is short, `repositories.py` is **not** part of this task (S1-T5 owns OSV writes).

## Definition of Done

- [ ] `schema.sql`, `connection.py`, tests merged.
- [ ] 3NF review recorded in the MR.
- [ ] `initialize_database` idempotent and creates `~/.pyreach` if absent.
- [ ] No raw string interpolation of anything except the DDL script.
