# ADR-001/002/003 — Modelo de datos implementado vs. diseño inicial (Práctica 6)

Fecha: 2026-10-07
Estado: Aceptado
Contexto: Práctica 6 — Diseño de datos vs. `pyreach/db/schema.sql`

## ADR-001 — Desnormalización `package_name` en `advisories`

- **Decisión:** No crear tabla `package` independiente. `advisories(package_name TEXT NOT NULL, ecosystem DEFAULT 'PyPI')` desnormalizado, normalizado en ingesta PEP 503 (lower + colapso `[-_.]`).
- **Motivo:** RNF-03 ≤45s en pipeline CI. Point query `WHERE package_name=?` con `idx_advisories_package` resuelve en <0.2 ms sin JOINs. Tabla separada añade JOIN por cada lookup y rompe S1-2 ya cerrado.
- **Tradeoff:** Transitiva teórica (3FN). Mitigado con UNIQUE `osv_id` y normalización en `importer.py`.
- **Evidencia:** `EXPLAIN QUERY PLAN` muestra `SEARCH advisories USING INDEX idx_advisories_package`.

## ADR-002 — Fusión `affected_range` + `vulnerable_symbol` → `affected_symbols`

- **Decisión:** Una fila por `(advisory_id, symbol_fqn, introduced, fixed, fixed_inclusive)` en `affected_symbols`.
- **Motivo:** OSV entrega `(symbol, range)` acoplados. Separar en dos tablas duplica FKs y obliga doble JOIN en `VulnerabilityMapper.find_by_package_and_version`. `version_fixed_inclusive` (0=fixed exclusivo, 1=last_affected inclusivo) preserva semántica OSV sin segunda tabla.
- **Evidencia:** `pyreach/osv/mapper.py:is_version_affected` valida `packaging.Version` con ambas semánticas.

## ADR-003 — Caché `cg_nodes/cg_edges/file_hashes` y `reachability_results`; `scan_execution` diferido

- **Decisión:** `cg_nodes/cg_edges/file_hashes` persistidos como **caché opcional** (primario: NetworkX DiGraph en RAM). `reachability_results(symbol_fqn, entry_point_fqn, max_depth, result, path_json)` es caché efímera invalidable. No se implementa `scan_execution(id_scan, commit, reduction_rate, exit_code)` ni `reachability_finding(call_trace json_extract)` históricos.
- **Motivo:** PyReach es scanner local-first, no SIEM. Histórico completo consume 1.5 sprints y viola restricción 480 HH / 8 semanas / Sprint 4 (presupuesto S/3500). Caché acelera re-escaneos incrementales (<45s tras `file_hashes` hit); histórico SIEM queda como Trabajo Futuro.
- **Backup:** `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;` por conexión en `pyreach/db/connection.py` + `scripts/backup.py` vía `Connection.backup()` con `wal_checkpoint`. Retención 14/30 d y RTO/RPO enterprise delegados al despliegue Lidercom (off-runner), no al código CLI de un usuario.
- **Validación:** No se implementa auditoría 10% SHA-256 (~1.520 registros). Se valida por tests de muestreo, `packaging` y `PRAGMA foreign_keys=ON` (CASCADE impide huérfanas). 10% SHA-256 queda Trabajo Futuro.

## Índices y constraints implementados

10 índices B-Tree en `schema.sql`: `idx_advisories_{package,cve,severity,modified}`, `idx_affected_symbols_{advisory,fqn}`, `idx_cg_nodes_{fqn,file}`, `idx_cg_edges_{caller,callee}`, `idx_reachability_{symbol,entry}`.
`reachability_results.max_depth CHECK (1..5)` y `result CHECK (REACHABLE/NOT_REACHABLE/POTENTIALLY_REACHABLE)` alineados a `pyreach/reachability/contracts.py:14`.

## Consecuencia

`document/practicas/practica6.tex` reescrito para reflejar este ADR. Validado por tutor el 2026-10-07 antes de tocar código (peer-review del council).
