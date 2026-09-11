# S2-T3 — Implement `PackageResolver` mapping package names to site-packages paths

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 6 h |
| Dependencies | S1-T1 (`Dependency`), S1-T4 |
| Related docs | `02-system-architecture.md` §site-packages Resolver; `05-data-model-and-storage.md` §Data Access Layer; `03-technical-specifications.md` §4 (`--db-path`, sites) |

## Purpose

Given the parsed dependency names, locate each installed package's source root in the active
environment or a target virtualenv. Sprint 3 needs these paths to parse library ASTs and build
cross-package call edges (e.g. `requests.get -> requests.api.get`).

## Preconditions

- S2-T2 merged.
- A test virtualenv or a set of fake `site-packages` directories available.
- `importlib.metadata` (stdlib) usable.

## Essential Sub-tasks

### 3.1 Define the resolver API and result model (0.5 h)

In `pyreach/loaders/packages.py`:

```python
@dataclass(frozen=True)
class InstalledPackage:
    name: str          # normalized distribution name
    version: str
    location: Path     # directory containing the importable package
    top_level: list[str]

class PackageResolver:
    def __init__(self, search_paths: list[Path] | None = None) -> None: ...
    def resolve(self, name: str) -> InstalledPackage | None: ...
    def resolve_all(self, deps: list[Dependency]) -> dict[str, InstalledPackage]: ...
```

### 3.2 Implement distribution discovery (2 h)

- Use `importlib.metadata.distributions(path=search_paths)` to enumerate installed dists.
- For each dist: `metadata["Name"]`, `dist.version`, `dist.locate_file("")`,
  and `dist.read_text("top_level.txt")` (may be absent).
- Normalize names with `normalize_name` so `Django` matches `django`.
- Build a dict `name -> InstalledPackage` once, reuse across `resolve` calls (cache).

### 3.3 Handle missing / partial metadata (1.5 h)

- If `top_level.txt` is missing, infer top-level modules by scanning the dist's
  `RECORD`/`files` for `*/__init__.py` and top-level `.py` files.
- If a package is installed as an editable install (`*.egg-link`, `direct_url.json`), record
  the linked source directory.
- If a dependency is not installed, return `None` and let the caller emit a WARNING
  (never fail the whole scan).

### 3.4 Support explicit search paths / virtualenvs (1 h)

- Accept `search_paths` pointing at `<venv>/Lib/site-packages` (Windows) or
  `<venv>/lib/pythonX.Y/site-packages` (POSIX).
- Provide `detect_site_packages(project_root: Path) -> list[Path]` that checks:
  1. `project_root/.venv/...`, 2. `project_root/venv/...`, 3. `sys.path` defaults.
- Document that resolving the *target project's* venv requires the correct Python version; if
  missing, fall back to the current environment with a WARNING.

### 3.5 Write tests (1 h)

Create `tests/unit/loaders/test_packages.py`:

| Test | Assertion |
|------|-----------|
| `test_resolve_installed_stdlib_like` | resolves a known installed dist |
| `test_missing_package_returns_none` | unknown name -> `None` |
| `test_name_normalization` | `Foo_Bar` matches `foo-bar` |
| `test_top_level_inference_without_txt` | infers via RECORD |
| `test_editable_install` | `direct_url.json` recorded |
| `test_detect_venv_site_packages` | finds `.venv` path when present |
| `test_resolve_all_mixed` | installed + missing deps handled |
| `test_cache_reuse` | second resolve does not rescan (spy on metadata) |

For determinism, construct a fake dist-info directory under `tmp_path` with `METADATA`,
`top_level.txt`, and a package dir; pass it via `search_paths`.

## Deliverables

- `pyreach/loaders/packages.py`
- `tests/unit/loaders/test_packages.py`

## Acceptance Criteria

- Resolves 100% of installed packages in a test venv. ✅ (roadmap S2-T3)
- Correctly maps all packages in a uv virtual environment. ✅ (roadmap Sprint 2 DoD)
- Missing packages degrade gracefully with warnings.

## Verification

```bash
uv run pytest tests/unit/loaders/test_packages.py -q
uv run python -c "from pyreach.loaders.packages import PackageResolver; r=PackageResolver(); print(r.resolve('networkx'))"
```

## Edge Cases & Pitfalls

- Distribution name (`PyYAML`) differs from import name (`yaml`) — always rely on
  `top_level.txt`/RECORD, never assume name equality.
- Namespace packages span multiple directories; `top_level` may list several.
- `locate_file("")` may point at `dist-info` parent, not the package itself; verify with
  `top_level`.
- Windows vs POSIX case sensitivity of paths.

## Risks / Scope Cuts

- **R7**: if metadata inference is brittle, restrict to `top_level.txt` and warn on the rest;
  document the limitation.

## Definition of Done

- [ ] Resolver + tests merged.
- [ ] Tested against a real uv virtual environment (networkx, jsonschema).
- [ ] Graceful degradation verified.
- [ ] Coverage >=85% on `loaders/`.
