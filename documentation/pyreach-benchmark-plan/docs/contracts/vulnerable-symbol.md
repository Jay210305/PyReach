# Contract C-SYMBOL 1.0.0 — advisory → vulnerable symbol

## Boundary
OSV/PyPI package version advisories alone are not guaranteed to name vulnerable Python functions. This **benchmark harness** provides separately reviewed symbol provenance; it must not silently invent an OSV extension column or mutate the existing PyReach DB schema without S0 audit and a separate accepted ADR.

## Record
```json
{"schema_version":"1.0.0","advisory_id":"FIXTURE-001","ecosystem":"PyPI","distribution":"demo-vulnpkg","installed_version":"1.0.0","symbol":"demo_vulnpkg.parser:unsafe_load","source_url":"https://example.org/reviewed-fixture","source_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","evidence_type":"manual_source_review","reviewed":true,"confidence":"verified","notes":"Synthetic controlled test; no real CVE claimed"}
```
`source_commit` may be null for referenced advisory web pages but must carry another retrievable immutable evidence hash. `confidence`: `verified/uncertain`; `reviewed` bool; `evidence_type`: `manual_source_review/public_sample/annotated_test`. `distribution` normalized by PEP 503; import name independently verified. `installed_version` explicit exact version (not inferred from broad range).

## Valid/invalid
Above is a valid **synthetic schema example** (example.org is not a source for real claims). Invalid: `{"advisory_id":"CVE-...","symbol":"yaml.load","reviewed":false,"confidence":"verified"}` → `SYMBOL_UNVERIFIED`; **unreviewed must not be verified**. Public Safety sample with incompatible license → `LICENSE_RESTRICTED` regardless of its quality.

## Fixtures and safe mode
36 source fixtures are locally constructed non-exploit examples. If PyReach cannot ingest test-specific advisory→symbol evidence without altering production logic, use a documented isolated adapter/DB fixture after auditing its real SQLite ingestion schema; otherwise record `unsupported`, not a forced positive or negative.
