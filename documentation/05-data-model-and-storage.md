# Data Model and Storage

## Overview

PyReach uses **SQLite** as its sole persistent storage engine. This choice satisfies the zero-configuration, fully local, data-sovereign requirement while providing sufficient performance for the OSV advisory dataset and optional call graph caching.

## Database File Locations

| Environment | Default Path | Override |
|-------------|--------------|----------|
| Developer workstation | `~/.pyreach/osv.db` | `--db-path` CLI flag |
| CI/CD runner | `/opt/pyreach/osv.db` (pre-seeded) | `--db-path` or env var `PYREACH_DB_PATH` |
| Project-specific | `<PROJECT_ROOT>/.pyreach/local.db` | `.pyreach.yml` config |

## Entity Relationship Diagram

```
+---------------+       +-------------------+       +---------------+
|  advisories   |<------| affected_symbols  |       |   cg_nodes    |
+---------------+       +-------------------+       +---------------+
| id (PK)       |       | id (PK)           |       | id (PK)       |
| osv_id (UQ)   |       | advisory_id (FK)  |       | node_fqn (UQ) |
| cve_id        |       | symbol_fqn        |       | file_path     |
| package_name  |       | version_introduced|       | line_number   |
| ecosystem     |       | version_fixed     |       | node_type     |
| severity_score|       +-------------------+       +---------------+
| severity_level|
| summary       |       +-------------------+       +---------------+
| published_date|       |    cg_edges       |       |reachability_  |
| aliases       |       +-------------------+       |   results     |
+---------------+       | id (PK)           |       +---------------+
                        | caller_id (FK)    |       | id (PK)       |
                        | callee_id (FK)    |       | symbol_fqn    |
                        | edge_type         |       | entry_point   |
                        | confidence        |       | result        |
                        +-------------------+       | max_depth     |
                                                    | path_json     |
                                                    | computed_at   |
                                                    +---------------+
```

## Schema Definition (DDL)

```sql
-- ============================================================
-- Advisories
-- Stores vulnerability records ingested from OSV JSON dumps.
-- ============================================================
CREATE TABLE IF NOT EXISTS advisories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    osv_id TEXT NOT NULL UNIQUE,
    cve_id TEXT,
    package_name TEXT NOT NULL,
    ecosystem TEXT NOT NULL DEFAULT 'PyPI',
    severity_score REAL,
    severity_level TEXT CHECK(severity_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    summary TEXT,
    published_date TEXT,  -- ISO 8601 format (YYYY-MM-DD)
    aliases TEXT,         -- JSON array of strings
    modified_date TEXT,   -- For incremental sync
    raw_json TEXT         -- Full OSV record for debugging/auditing
);

CREATE INDEX IF NOT EXISTS idx_advisories_package ON advisories(package_name);
CREATE INDEX IF NOT EXISTS idx_advisories_cve ON advisories(cve_id);
CREATE INDEX IF NOT EXISTS idx_advisories_severity ON advisories(severity_level);
CREATE INDEX IF NOT EXISTS idx_advisories_modified ON advisories(modified_date);

-- ============================================================
-- Affected Symbols
-- Maps each advisory to the specific functions/classes/methods
-- that contain the vulnerability.
-- ============================================================
CREATE TABLE IF NOT EXISTS affected_symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisory_id INTEGER NOT NULL,
    symbol_fqn TEXT NOT NULL,  -- e.g., "requests.sessions.Session.request"
    version_introduced TEXT,
    version_fixed TEXT,
    FOREIGN KEY (advisory_id) REFERENCES advisories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_affected_symbols_advisory ON affected_symbols(advisory_id);
CREATE INDEX IF NOT EXISTS idx_affected_symbols_fqn ON affected_symbols(symbol_fqn);

-- ============================================================
-- Call Graph Nodes
-- Optional persistence for very large repositories.
-- In-memory NetworkX is primary; SQLite used for caching across runs.
-- ============================================================
CREATE TABLE IF NOT EXISTS cg_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_fqn TEXT NOT NULL UNIQUE,  -- "package.module.Class.method"
    file_path TEXT,
    line_number INTEGER,
    node_type TEXT CHECK(node_type IN ('FUNCTION', 'METHOD', 'CLASS', 'LAMBDA'))
);

CREATE INDEX IF NOT EXISTS idx_cg_nodes_fqn ON cg_nodes(node_fqn);
CREATE INDEX IF NOT EXISTS idx_cg_nodes_file ON cg_nodes(file_path);

-- ============================================================
-- Call Graph Edges
-- Directed invocation relationships.
-- ============================================================
CREATE TABLE IF NOT EXISTS cg_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id INTEGER NOT NULL,
    callee_id INTEGER NOT NULL,
    edge_type TEXT CHECK(edge_type IN ('STATIC', 'DYNAMIC', 'INHERITANCE', 'IMPORT')),
    confidence REAL DEFAULT 1.0 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    FOREIGN KEY (caller_id) REFERENCES cg_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (callee_id) REFERENCES cg_nodes(id) ON DELETE CASCADE,
    UNIQUE(caller_id, callee_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_cg_edges_caller ON cg_edges(caller_id);
CREATE INDEX IF NOT EXISTS idx_cg_edges_callee ON cg_edges(callee_id);

-- ============================================================
-- Reachability Results Cache
-- Memoizes reachability analysis to speed up repeated scans.
-- Invalidated when call graph or advisories change.
-- ============================================================
CREATE TABLE IF NOT EXISTS reachability_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_fqn TEXT NOT NULL,
    entry_point_fqn TEXT NOT NULL,
    result TEXT CHECK(result IN ('REACHABLE', 'NOT_REACHABLE', 'POTENTIALLY_REACHABLE')),
    max_depth INTEGER,
    path_json TEXT,  -- JSON array of node_fqn strings representing the path
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol_fqn, entry_point_fqn, max_depth)
);

CREATE INDEX IF NOT EXISTS idx_reachability_symbol ON reachability_results(symbol_fqn);
CREATE INDEX IF NOT EXISTS idx_reachability_entry ON reachability_results(entry_point_fqn);
```

## Data Access Layer (Python)

### Connection Manager

```python
# pyreach/db/connection.py
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

class DatabaseError(Exception):
    pass

@contextmanager
def get_db_connection(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """Yields a SQLite connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise DatabaseError(f"Database operation failed: {exc}") from exc
    finally:
        conn.close()
```

### Repository Pattern

```python
# pyreach/db/repositories.py
from dataclasses import asdict
from typing import List, Optional
import json

class AdvisoryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert(self, advisory: "Vulnerability") -> int:
        sql = """
            INSERT INTO advisories (osv_id, cve_id, package_name, ecosystem,
                                    severity_score, severity_level, summary,
                                    published_date, aliases, modified_date, raw_json)
            VALUES (:osv_id, :cve_id, :package_name, :ecosystem,
                    :severity_score, :severity_level, :summary,
                    :published_date, :aliases, :modified_date, :raw_json)
            ON CONFLICT(osv_id) DO UPDATE SET
                severity_score=excluded.severity_score,
                severity_level=excluded.severity_level,
                summary=excluded.summary,
                modified_date=excluded.modified_date,
                raw_json=excluded.raw_json;
        """
        params = asdict(advisory)
        params["aliases"] = json.dumps(params.get("aliases", []))
        cursor = self._conn.execute(sql, params)
        return cursor.lastrowid

    def find_by_package_and_version(
        self, package_name: str, version: str
    ) -> List["Vulnerability"]:
        # Version range matching is done in Python using `packaging` library
        # after fetching candidates by package name.
        sql = "SELECT * FROM advisories WHERE package_name = ?;"
        rows = self._conn.execute(sql, (package_name,)).fetchall()
        return [self._row_to_vuln(r) for r in rows]

    def _row_to_vuln(self, row: sqlite3.Row) -> "Vulnerability":
        ...
```

## OSV Ingestion Algorithm

### Incremental Sync Flow

```
1. Read last_sync timestamp from SQLite (metadata table or file mtime).
2. Stream OSV JSONL dump line by line.
3. For each record:
   a. Skip if record["modified"] <= last_sync.
   b. Skip if affected[].package.ecosystem != "PyPI".
   c. Normalize package name: lower(), replace('_', '-'), replace('.', '-').
   d. Upsert advisories table.
   e. For each affected range + symbol, upsert affected_symbols table.
4. Update last_sync timestamp.
5. VACUUM if fragmentation > 20%.
```

### Version Range Handling

OSV uses `events` (introduced, fixed, last_affected, limit). PyReach stores these strings and evaluates version containment at query time using the `packaging` library:

```python
from packaging.version import Version
from packaging.specifiers import SpecifierSet

def is_version_affected(version: str, introduced: Optional[str], fixed: Optional[str]) -> bool:
    v = Version(version)
    if introduced and v < Version(introduced):
        return False
    if fixed and v >= Version(fixed):
        return False
    return True
```

## Call Graph Persistence Strategy

### Decision: In-Memory Primary, SQLite Cache Secondary

| Factor | In-Memory NetworkX | SQLite Persistence |
|--------|-------------------|-------------------|
| Speed | Very fast traversal | Slower (disk I/O) |
| Memory | High for large graphs | Low |
| Cross-run reuse | None | Yes |
| Complexity | Simple | Requires sync logic |

**Chosen approach**: Build NetworkX `DiGraph` in memory for each scan. Optionally serialize to SQLite at the end for caching. On subsequent scans, check if source files changed (via hash) before rebuilding.

### File Change Detection

```sql
CREATE TABLE IF NOT EXISTS file_hashes (
    file_path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Before building the call graph:
1. Compute SHA256 of every `.py` file.
2. Compare with `file_hashes` table.
3. If all match and `use_cache` is enabled, load `cg_nodes` and `cg_edges` from SQLite into NetworkX.
4. Otherwise, rebuild and persist new hashes.

## Performance Projections

| Dataset Size | SQLite Size | Ingestion Time | Query Time (by package) |
|--------------|-------------|----------------|-------------------------|
| 10,000 advisories | ~30 MB | ~3 minutes | <10 ms |
| 50,000 advisories | ~150 MB | ~15 minutes | <20 ms |
| 100,000 advisories | ~300 MB | ~30 minutes | <30 ms |

*Note: Query times assume indexed `package_name` lookups. Version range filtering adds ~1-5 ms per advisory candidate.*

## Backup and Migration

- **Backup**: The OSV DB is a single file; copy via standard filesystem tools. Lidercom runner should backup weekly.
- **Migrations**: Use simple integer versioning in a `schema_version` table. Apply sequential SQL scripts from `pyreach/db/migrations/`.

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT INTO schema_version (version) VALUES (1);
```

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
