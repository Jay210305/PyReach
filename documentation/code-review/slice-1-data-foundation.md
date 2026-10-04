# Slice 1 — Data foundation

- Scope: `pyreach/parsers/ pyreach/osv/ pyreach/db/`
- Diff: `git diff c03e073...HEAD -- pyreach/parsers pyreach/osv pyreach/db` (~1,085 lines)
- Spec: `documentation/implementation/sprint-1-data-foundation/` (S1-T1..T6; T0/T7 out of scope)
- Commits: ef594db, 09193e0, 81b8b40, 31e75ef, 13769a8
- Date: 2026-10-02

## Standards

Overall: conventions are largely respected — PEP 503 `normalize_name` is correct, no
eval/exec, `Dependency` is `frozen=True`, ConfigError/ParseError/OSVError taxonomy matches
AGENTS.md §12, traversal is iterative.

### Hard violations (documented standards)

- **`pyreach/osv/mapper.py` missing — layout/contract deviation**
  (`pyreach/db/repositories.py:90`, `pyreach/parsers/osv_json.py:13`). AGENTS.md §6 and
  doc 03 §2 place the `Vulnerability` contract *and* "advisory lookup by package/version"
  in `osv/mapper.py`. Implementation puts `Vulnerability` in `parsers/osv_json.py` and
  lookup in `db/repositories.py`, which also inverts layering (db → parsers imports,
  `repositories.py:6-7`). Docs are source of truth per AGENTS.md; either create
  `mapper.py` or amend doc 03.
- **`last_affected` treated as `fixed`** (`pyreach/parsers/osv_json.py:90-91`):
  `fixed = str(event["last_affected"])`. OSV `last_affected` is the *last vulnerable*
  version, so `is_version_affected(v == last_affected)` returns False — a false negative,
  breaching AGENTS.md §1 "zero critical false negatives; uncertainty resolves upward."
- **Comments where docstrings suffice** (AGENTS.md §11 "no comments unless a non-obvious
  algorithm demands one"): `# Local directory or relative/absolute path`
  (`manifest.py:132`), `#: ...keeps future typing migrations cheap` (`manifest.py:61-62`).
  Nit-level but documented.

### Judgement calls (baseline smells)

- **Duplicated Code**: the `include_non_pypi` → `dependencies[name] = Dependency(...)`
  block appears three times verbatim (`manifest.py:194-198, 206-210, 222-224`) — extract
  one helper. The symbol-aggregation loop (dedupe symbols, first non-None intro/fix) is
  duplicated between `parse_osv_record` (`osv_json.py:~192`) and
  `find_by_package_and_version` (`repositories.py:~110-125`).
- **Speculative Generality**: `ParserResult = list[Dependency]` (`manifest.py:63`) exists
  only for hypothetical "future typing migrations"; `ManifestParser.supports()`
  (`manifest.py:80`) is never called — `select_manifest_parser` (`manifest.py:345`)
  hard-codes filenames, contradicting the protocol's own docstring ("without hard-coded
  logic").
- **Data Clumps / Primitive Obsession**: unnamed `tuple[str, str | None, str | None]`
  triples travel through `extract_affected` → `replace_symbols` → repos; `upsert`'s
  `modified_date/published_date/aliases/raw_json` (`repositories.py:17-22`) always travel
  together from importer — a small `AffectedSymbol` dataclass / raw-record bundle would
  name these concepts.
- **Nit**: `iter_osv_records` (`importer.py:28`) yields `(dict | None, bool)` where
  `record is None ⟺ malformed` — redundant flag; yield `dict | None`.
- **Nit**: URL-scheme tuple `("http://","https://","ftp://")` duplicated
  (`importer.py:120`, `manifest.py:205`).
- **Nit**: `get_db_connection` (`connection.py:31-34`) wraps *caller* exceptions into
  `DatabaseError(OSVError)`, blurring §12 taxonomy — a repository bug will surface as a
  corrupt-DB error.

## Spec

### Missing or wrong requirements

1. **[Critical]** `osv_json.py:90-91` — `last_affected` is stored into the exclusive
   `fixed` slot. S1-T5: *"`last_affected` is inclusive; `fixed` is exclusive — do not
   confuse them."* A package at exactly `last_affected` is judged NOT affected — a false
   negative, violating the project's "zero critical false negatives" rule.
   `tests/unit/parsers/test_osv_json.py:161` locks the wrong behavior in.
2. **[Critical]** `osv_json.py:81-91` — range events overwrite a single
   `introduced`/`fixed` pair; only the **last** pair survives. S1-T5 §5.2: *"walk
   `events[]` accumulating `introduced` → `fixed` / `last_affected` pairs."* Multi-range
   advisories (e.g. 1.0→1.5, 2.0→2.1) report 1.2 as unaffected.
3. **[Critical]** `osv_json.py:155-168` — real OSV `severity[].score` is a CVSS **vector
   string** (`"CVSS:3.1/AV:N/..."`); `float()` always fails, so `severity_score` is
   `None` for real dumps. S1-T5 §5.1: *"from `severity[]` CVSS vector + score; map
   `CVSS:3.1` scores → LOW/MEDIUM/HIGH/CRITICAL"*; §pitfalls: *"prefer CVSS v3.1 then v4
   then v2"* — `type` is never inspected.
4. **[Improvement]** `osv_json.py:83` — explicit `versions[]` lists ignored. S1-T5
   pitfalls: *"`versions[]` (explicit list) must also be honored, not just `ranges[]`."*
5. **[Improvement]** `importer.py:28-45` — JSON-array dump files unsupported (whole file
   counts as one malformed line). S1-T5 §5.3: *"Support both **JSONL** … and a JSON array
   file."*
6. **[Improvement]** `importer.py:67-83` — incremental mode derives the watermark from
   `MAX(modified_date)` and never persists one. S1-T5 §5.4: *"read last sync from
   `schema_version` metadata or a dedicated `sync_metadata` row … Update timestamp after
   a successful full pass."* Also, incremental-skipped records inflate `stats.total`
   with no matching bucket.
7. **[Improvement]** `importer.py:65` — whole file is one transaction; no *"Batch commits
   every N records (e.g. 1000)"* (§5.4), and the §5.7 10k-record
   `@pytest.mark.performance` test is absent despite DoD *"10k-record benchmark
   documented"*.
8. **[Nit]** `manifest.py:176-191` — `-r` skipped silently; S1-T2 §2.4: *"either recurse
   (bounded depth) or skip with warning — document choice."*
9. **[Nit]** `importer.py:91` — full `published` timestamp stored; §5.1 says *"(date part
   only)"*. Also dict-but-invalid records (no `id`) count as `skipped_ecosystem`, not
   `skipped_malformed` (`importer.py:86-88`).

### Scope creep (benign)

- Extra pip flags skipped (`--no-index` etc., `manifest.py:183-189`).
- `DatabaseError(OSVError)` vs doc 05's `DatabaseError(Exception)`.
- Upsert updates more columns than doc 05's pattern.

### Conformant

S1-T1 contract, S1-T3 PipfileLockParser + `select_manifest_parser`, S1-T4 schema
(verbatim DDL, 7 tables, indexes, idempotent init).

## Summary

- Standards: 9 findings — worst: `last_affected` stored as exclusive `fixed` (false
  negative, breaches AGENTS.md §1).
- Spec: 12 findings — worst: same `last_affected`/`fixed` inversion plus multi-range
  overwrite in `osv_json.py:81-91`, locked in by a test.
