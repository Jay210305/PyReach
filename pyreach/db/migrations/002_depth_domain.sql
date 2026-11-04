BEGIN IMMEDIATE;
ALTER TABLE reachability_results RENAME TO legacy_reachability_results;
DROP INDEX IF EXISTS idx_reachability_symbol;
DROP INDEX IF EXISTS idx_reachability_entry;
CREATE TABLE reachability_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_fqn TEXT NOT NULL,
    entry_point_fqn TEXT NOT NULL,
    result TEXT CHECK(result IN ('REACHABLE', 'NOT_REACHABLE', 'POTENTIALLY_REACHABLE')),
    max_depth INTEGER CHECK(max_depth IS NULL OR (max_depth BETWEEN 0 AND 7)),
    path_json TEXT,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol_fqn, entry_point_fqn, max_depth)
);
INSERT INTO reachability_results SELECT * FROM legacy_reachability_results;
DROP TABLE legacy_reachability_results;
CREATE INDEX idx_reachability_symbol ON reachability_results(symbol_fqn);
CREATE INDEX idx_reachability_entry ON reachability_results(entry_point_fqn);
COMMIT;
