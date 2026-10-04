-- ============================================================
-- PyReach Database Schema (SQLite 3NF)
--
-- Normal Form Documentation:
-- 1NF: All attributes are atomic. No repeating groups.
-- 2NF: All non-key attributes are fully functionally dependent on the PK.
-- 3NF: No transitive dependencies on non-key attributes. Advisory facts
--      reside strictly in `advisories`; symbol facts in `affected_symbols`.
--      `raw_json` in `advisories` is retained for audit/debugging only.
-- ============================================================

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
    -- 0 = fixed (exclusive upper bound), 1 = last_affected (inclusive)
    version_fixed_inclusive INTEGER NOT NULL DEFAULT 0,
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

-- ============================================================
-- File Hashes
-- SHA256 change detection for call graph caching.
-- ============================================================
CREATE TABLE IF NOT EXISTS file_hashes (
    file_path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Schema Version
-- Integer migration tracking.
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);

-- ============================================================
-- Sync Metadata
-- Key/value store for importer bookkeeping (e.g. last sync watermark).
-- ============================================================
CREATE TABLE IF NOT EXISTS sync_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
