# S1-T0 — Project environment bootstrap with uv (all dependencies)

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 1 h |
| Dependencies | None — this is the **first** task; every other task assumes it |
| Related docs | `03-technical-specifications.md` §1, §Technology Stack; `08-testing-strategy.md` §3; `AGENTS.md` |

## Purpose

Allocate the complete, pinned dependency set into the project's local `.venv` using **uv**,
so every subsequent task can run tests, lint, and type checks immediately. This replaces the
Poetry-based setup in the original technical spec; uv is now the single project/dependency
manager.

## Preconditions

- `uv` installed (`uv --version` >= 0.5). The repo was bootstrapped with uv 0.12.6.
- A `.venv` already exists at the repo root (created by `python -m venv .venv` on
  Python 3.14.7). uv will adopt it as the project environment.
- `requires-python = ">=3.10"`; the local interpreter is 3.14, which satisfies it.

## Essential Sub-tasks

### 0.1 Author `pyproject.toml` (already applied) (0.25 h)

The root `pyproject.toml` defines the full dependency set:

**Runtime (`[project].dependencies`)**

| Package | Spec | Why |
|---------|------|-----|
| `networkx` | `>=3.0` | call graph `DiGraph` (Sprint 3) |
| `jsonschema` | `>=4.0` | SARIF v2.1.0 validation (Sprint 4) |
| `packaging` | `>=23.0` | manifest version parsing, version ranges (Sprint 1) |
| `pyyaml` | `>=6.0` | `.pyreach.yml` config loader (S4-T5) |

**Dev (`[dependency-groups].dev`)**

| Package | Spec | Why |
|---------|------|-----|
| `pytest` | `>=7.0` | test runner |
| `pytest-cov` | `>=4.0` | coverage |
| `pytest-xdist` | `>=3.0` | parallel tests |
| `factory-boy` | `>=3.3` | test data generation |
| `freezegun` | `>=1.0` | time mocking |
| `black` | `>=23.0` | formatter |
| `mypy` | `>=1.0` | static typing |
| `ruff` | `>=0.1.0` | linter |

Notes:
- `[tool.uv] package = false` because the `pyreach/` package does not exist yet. Change to
  `true` and add a `[build-system]` (hatchling) once S2-T4 creates `pyreach/`.
- `uv.lock` is committed at the repo root to make installs reproducible.

### 0.2 Sync the environment (0.25 h)

```powershell
uv sync          # installs runtime + dev into .venv from uv.lock
uv run python -c "import networkx, jsonschema, packaging, yaml, pytest, mypy, ruff; print('deps-ok')"
```

- `uv sync` is destructive-by-design: it makes `.venv` exactly match the lock.
- Use `uv sync --no-dev` to install runtime only (e.g. the CI scan stage in Sprint 4).
- Use `uv sync --locked` in CI to fail when the lock is stale.

### 0.3 Standard developer commands (0.25 h)

```powershell
# Add/remove dependencies (updates pyproject.toml + uv.lock)
uv add <package>
uv add --dev <package>        # or: uv add --group dev <package>
uv remove <package>

# Run anything inside .venv without activating it
uv run pytest
uv run ruff check .
uv run mypy pyreach

# Re-lock after manual pyproject edits
uv lock
```

Activation (optional):

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# POSIX
source .venv/bin/activate
```

### 0.4 Add `.gitignore` (already applied) (0.25 h)

The root `.gitignore` excludes `.venv/`, caches, coverage artifacts, and PyReach runtime data
(`.pyreach/`, `*.sarif`, `*.db`) while keeping `uv.lock` committed.

## Deliverables

- `pyproject.toml`
- `uv.lock` (committed)
- `.gitignore`
- A synced `.venv` containing all runtime + dev dependencies.

## Acceptance Criteria

- `uv sync` exits 0 and `.venv` contains all 34 resolved packages.
- `uv run python -c "import networkx, jsonschema, packaging, yaml"` prints `deps-ok`.
- `uv run pytest --version`, `uv run ruff --version`, `uv run mypy --version` all work.
- `uv.lock` is committed to git.

## Verification

```powershell
uv --version
uv sync
uv run python -c "import networkx, jsonschema, packaging, yaml, pytest, mypy, ruff; print('deps-ok')"
uv run pytest --version
```

## Edge Cases & Pitfalls

- The venv was created by `python -m venv` (not `uv venv`); uv still adopts it because it is
  named `.venv` at the project root. If uv ever complains, delete `.venv` and run `uv venv`.
- Do **not** commit `.venv/`. Do commit `uv.lock`.
- Python 3.14 is the dev interpreter while the spec targets 3.10+; keep code free of 3.11+
  only syntax so the documented 3.10 support remains true.
- Some packages may not yet publish 3.14 wheels; if `uv sync` fails on a specific version,
  pin the newest version that supports 3.14 and document the deviation.
- Do not install packages with `pip install` into `.venv`; that desynchronizes it from
  `uv.lock`. Use `uv add`.

## Risks / Scope Cuts

- None. This task is a prerequisite for everything; it must be done first.

## Definition of Done

- [x] `pyproject.toml`, `uv.lock`, `.gitignore` committed.
- [x] `.venv` synced; all imports verified.
- [x] `uv run` works for pytest, ruff, and mypy.
- [x] `AGENTS.md` documents the same commands.
