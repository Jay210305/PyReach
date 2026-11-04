# PyReach

Local-first static reachability analysis for Python dependency vulnerabilities.
Parses Python without executing it, reads a local SQLite OSV catalog, builds an
interprocedural graph, classifies each affected symbol and emits SARIF 2.1.0,
JSON or text. Exit 0 means the selected policy did not block; it is not a
statement that the project is vulnerability-free.

## Start (Python 3.10+ and uv)

```sh
uv sync --locked
uv run pyreach --help
uv run pyreach sync-osv --source /approved/advisories.jsonl -d /approved/osv.db
uv run pyreach /path/to/project -m requirements.txt -d /approved/osv.db -f text
uv run pyreach /path/to/project -d /approved/osv.db --include-potentially -o results.sarif
```

`requirements.txt` and `Pipfile.lock` are supported. Installed versions and transitives
are resolved from the target project's `.venv`/`venv`, falling back explicitly to
the scanner environment. Keep the correct environment available; a manifest is not
proof that a dependency is installed. Unknown versions are evaluated conservatively.
No download is performed by `scan` or `sync-osv`: synchronization imports approved
local JSON/JSONL. A directory sync shares one watermark across all input files.

- `REACHABLE`: a static call path was found.
- `POTENTIALLY_REACHABLE`: dynamic calls, unresolved symbols, partial sources or
  exhausted depth prevent ruling out a path.
- `NOT_REACHABLE`: no path found within the modeled static scope; not a guarantee
  about arbitrary Python behavior or runtime exploitability.

Exit codes: **0** success/policy allows; **1** findings block; **2** operational or
configuration error. `--no-fail` suppresses findings gates, not operational errors.
The depth domain is **0..7**, default 5; 0 inspects entry points only. `--include-all`
retains static discards. `--exclude` is repeatable. `--cache`/`--no-cache` controls a
content-addressed JSON graph cache under `~/.cache/pyreach`. Relative output paths
are resolved against the project root. Source/manifest/DB/config overwrite is rejected.

See [user manual](documentation/manuals/user.md),
[installation](documentation/manuals/installation.md),
[maintenance and support](documentation/manuals/maintenance.md),
[CI templates](ci/README.md), and [delivery status](documentation/delivery-status.md).

## Configuration

`.pyreach.yml` (or `.pyreach.yaml`) in the project:

```yaml
pyreach:
  version: '1'
  manifest: requirements.txt
  max_depth: 5
  entry_points: [myapp.cli:main]
  ignore_paths: [tests/, docs/]
  thresholds:
    fail_on_reachable: true
    fail_on_potentially: true
```

Precedence: explicit CLI flags > project config > `~/.pyreach/config.yml` > defaults.
Entry points and ignores are additive. Unknown keys and wrong types fail explicitly.
YAML uses safe loading. Reports omit unknown physical source regions rather than
inventing a line number. Summary reduction counts an advisory as discarded only if
**all** its symbols are `NOT_REACHABLE`; human time savings remain unmeasured.

## Reproduce verification

```sh
uv run ruff check pyreach tests scripts/validate_release.py
uv run ruff format --check pyreach tests scripts/validate_release.py
uv run mypy pyreach
uv run pytest -m 'not performance' --cov=pyreach --cov-report=xml --cov-fail-under=80
uv run pytest -m performance
uv run bandit -r pyreach -ll
uv run pip-audit
uv run python scripts/validate_release.py --output release-evidence
uv build
```

The cached OASIS schema is `tests/fixtures/sarif-schema-2.1.0.json` (upstream:
https://github.com/oasis-tcs/sarif-spec/blob/main/sarif-2.1/schema/sarif-schema-2.1.0.json).
Tests do not need a live advisory service. The dependency-audit command needs public
advisory metadata access, separately from offline scanning.

## Limits and acceptance

Synthetic tests demonstrate behavior; they do not establish industrial false-positive
reduction, comprehensive Python soundness, Lidercom deployment, user acceptance or
manual validation by a third party. Runtime metaprogramming remains approximated.
Use explicit entry points for unsupported framework patterns. No production deployment,
user signature or financial measurement is fabricated in the release evidence.

### Refinamiento de sincronización incremental

La marca global se actualiza al terminar el conjunto y sirve como registro. La decisión
de omitir se compara contra la fecha del aviso ya persistido, no sólo contra la marca
global. Un aviso aún no importado se incorpora aunque su fecha sea anterior a la última
sincronización; una regresión adicional conserva ese contrato.
