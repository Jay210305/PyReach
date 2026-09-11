# S4-T5 — Implement `.pyreach.yml` parser and merge with CLI overrides

| Field | Value |
|-------|-------|
| Sprint | 4 — SARIF Serializer, CLI, and CI/CD Quality Gates |
| Owner | Jose Alonso Yanez |
| Effort | 4 h |
| Dependencies | S4-T3 |
| Related docs | `03-technical-specifications.md` §5; `07-sarif-and-cli-design.md` §2.5; `10-risk-and-contingency-plan.md` §3 (scope item 3) |

## Purpose

Allow projects to persist scan configuration in `.pyreach.yml` (entry points, ignore paths,
thresholds) so CI jobs stay short and consistent. This task is the **designated scope-cut
candidate** for Sprint 4; it is isolated behind a config resolver.

## Preconditions

- CLI orchestrator in place (S4-T3).
- A YAML parser available. `PyYAML` is not yet a dependency; add `pyyaml = "^6.0"` to
  `[project.dependencies]` (document the new dependency) or write a minimal parser for the
  restricted schema. Prefer `PyYAML` for correctness.

## Essential Sub-tasks

### 5.1 Define the config dataclass and schema (0.5 h)

In `pyreach/config.py`:

```python
@dataclass
class PyReachConfig:
    version: str = "1"
    entry_points: list[str] = field(default_factory=list)
    ignore_paths: list[str] = field(default_factory=list)
    max_depth: int = 5
    manifest: str = "requirements.txt"
    osv_db: str = "~/.pyreach/osv.db"
    thresholds: Thresholds = field(default_factory=Thresholds)

@dataclass
class Thresholds:
    fail_on_reachable: bool = True
    fail_on_potentially: bool = False
```

- Mirror the YAML in `03-...md` §5 exactly.
- Unknown keys -> `ConfigError` (strict validation) with the offending key.

### 5.2 Implement the loader (1.5 h)

```python
def load_config(project_root: Path) -> PyReachConfig | None:
    ...
```

- Look for `<project_root>/.pyreach.yml` then `<project_root>/.pyreach.yaml`.
- If both absent -> return `None` (use defaults).
- Parse with `yaml.safe_load` (never `yaml.load`); catch `yaml.YAMLError` -> `ConfigError`.
- Validate types (`max_depth` int >=0, lists of strings, `version` supported).
- Support `~` expansion for `osv_db`.

### 5.3 Implement precedence merging (1 h)

Per `07-...md` §2.5: **CLI flags > project `.pyreach.yml` > user-global config > defaults**.

```python
def resolve_config(cli_args: Namespace, project_root: Path) -> PyReachConfig:
    ...
```

- Only override a config value when the CLI flag was **explicitly provided**. Use
  `argparse` defaults of `None` (or a sentinel) so "not provided" is distinguishable from the
  literal default; apply built-in defaults last.
- `entry_points`, `exclude` are additive unions (config + CLI).
- `thresholds.fail_on_potentially` maps to `--include-potentially`; CLI flag OR config value.
- Record the effective config at DEBUG for troubleshooting.

### 5.4 Write tests (1 h)

Create `tests/unit/test_config.py`:

| Test | Assertion |
|------|-----------|
| `test_load_valid_config` | all fields populated |
| `test_missing_config_returns_none` | `None` |
| `test_malformed_yaml_raises_config_error` | `ConfigError` |
| `test_unknown_key_raises_config_error` | `ConfigError` |
| `test_bad_max_depth_type` | `ConfigError` |
| `test_cli_overrides_config` | CLI `-k 3` beats config `5` |
| `test_config_used_when_cli_absent` | config value applied |
| `test_entry_points_union` | config + CLI merged |
| `test_tilde_expansion` | `~/...` expanded |
| `test_thresholds_mapping` | `fail_on_potentially` -> flag behavior |
| `test_defaults_when_no_cli_no_config` | built-in defaults |

## Deliverables

- `pyreach/config.py`
- `tests/unit/test_config.py`
- `pyyaml` added to `pyproject.toml`.
- Sample `.pyreach.yml` fixture under `tests/fixtures/`.

## Acceptance Criteria

- Config file values correctly overridden by CLI flags. ✅ (roadmap S4-T5)
- Strict validation raises `ConfigError` (exit 2) rather than silently ignoring bad input.
- Loading is isolated so the feature can be removed if cut.

## Verification

```bash
uv run pytest tests/unit/test_config.py -q
uv run pyreach tests/fixtures/projects/linear_reachable -f text
```

## Edge Cases & Pitfalls

- YAML `1` parses as int, not str; coerce `version` to `str` or accept both.
- `safe_load` returns `None` for an empty file — treat as defaults, not an error.
- Windows home directory expansion differs; use `Path.expanduser()`.
- Distinguishing "flag absent" from "flag set to default" is the crux of precedence; centralize
  the sentinel in one place.

## Risks / Scope Cuts

- **Scope cut #3** (`10-risk-and-contingency-plan.md` §3): if Sprint 4 slips >3 days, postpone
  `.pyreach.yml` entirely and rely on CLI flags. Keeping `load_config` returning `None` by
  default makes this a no-op removal.

## Definition of Done

- [ ] Config loader + tests merged.
- [ ] Precedence rules match the spec.
- [ ] `PyYAML` dependency declared.
- [ ] Feature cleanly removable if cut.
