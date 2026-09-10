# S1-T1 — Design `Dependency` dataclass and parser interface

| Field | Value |
|-------|-------|
| Sprint | 1 — Dependency Parser, OSV Ingestion, TDD Fixtures |
| Owner | Julio Centeno |
| Effort | 4 h |
| Dependencies | None (entry point of Sprint 1) |
| Related docs | `03-technical-specifications.md` §3.1, §8; `02-system-architecture.md` §Input Layer |

## Purpose

Establish the **stable data contract** and the **abstract parser interface** that every
manifest parser must implement. Doing this first prevents churn later when both
`requirements.txt` and `Pipfile.lock` parsers are written and when the OSV mapper consumes
the parsed dependencies. The interface must be frozen before implementation begins.

## Preconditions

- Repository cloned; Python 3.10+ available.
- `pyproject.toml` exists with package `pyreach` (see `03-technical-specifications.md` §2).
- `pyreach/parsers/__init__.py` exists (can be empty).
- `pyreach/exceptions.py` exists (can be a stub).

## Essential Sub-tasks

### 1.1 Define the `Dependency` frozen dataclass (1.0 h)

Create `pyreach/parsers/manifest.py` with the exact contract from spec §3.1:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Dependency:
    name: str
    version: str
    source: str
    extra: Optional[str] = None
    marker: Optional[str] = None
```

- `name` MUST be PEP 503 normalized (lowercase; runs of `-`, `_`, `.` collapsed to `-`).
  Add a module-level helper `normalize_name(name: str) -> str` using `re.sub(r"[-_.]+", "-", name).lower()`.
- `version`: for exact pins keep the literal (`"2.31.0"`); for ranges store the **lower bound**
  resolved strip operator (`">=2.0.0"` -> `"2.0.0"`). Document this rule in the docstring.
- `source`: one of `"requirements.txt"` or `"Pipfile.lock"` (use constants, not literals).
- Make the dataclass `frozen=True` so it is hashable and safe as a dict key.
- Add `__post_init__` validation: `name` must be non-empty, `source` must be in the allowed set.
  Raise `ParseError` on violation.

### 1.2 Define parser result type (0.5 h)

Add a lightweight container or simply document that parsers return `list[Dependency]`.
Prefer returning a plain list for simplicity; add a module-level `ParserResult = list[Dependency]`
alias with a docstring to keep future typing migrations cheap.

### 1.3 Define the abstract parser protocol (1.0 h)

In the same module add an interface using `typing.Protocol` (avoids forcing inheritance):

```python
from pathlib import Path
from typing import Protocol, runtime_checkable

@runtime_checkable
class ManifestParser(Protocol):
    source_name: str
    def supports(self, path: Path) -> bool: ...
    def parse(self, path: Path) -> list[Dependency]: ...
```

- `supports()` lets the CLI auto-select a parser by filename without hard-coding logic.
- `parse()` MUST raise `ConfigError` when the file is missing and `ParseError` when malformed.
- Document that `parse()` never executes the file (no `eval`, no `pip`).

### 1.4 Extend the exception hierarchy (0.75 h)

In `pyreach/exceptions.py` define (or confirm) the base hierarchy from spec §8. At minimum
Sprint 1 needs:

```python
class PyReachError(Exception): ...
class ConfigError(PyReachError): ...
class ParseError(PyReachError): ...
class OSVError(PyReachError): ...
```

Leave `AnalysisError` / `OutputError` placeholders for later sprints.

### 1.5 Write contract tests before implementation (0.5 h)

Create `tests/unit/parsers/test_manifest_contract.py`:

- `test_dependency_is_frozen` — assigning to `name` raises `FrozenInstanceError`.
- `test_dependency_normalizes_name` — `normalize_name("Foo_Bar.Baz") == "foo-bar-baz"`.
- `test_dependency_rejects_empty_name` — raises `ParseError`.
- `test_dependency_rejects_unknown_source` — raises `ParseError`.
- `test_manifest_parser_is_protocol` — a dummy class with `source_name/supports/parse`
  satisfies `isinstance(dummy, ManifestParser)` (thanks to `runtime_checkable`).

These tests are the executable form of this task's acceptance criteria.

### 1.6 Peer review with Alonso (0.25 h)

Open a merge request containing only the interface + tests. Alonso reviews and signs off in
the MR thread. Record the review hint in the commit message (e.g. `S1-T1 reviewed-by: Alonso`).

## Deliverables

- `pyreach/parsers/manifest.py` (dataclass + `normalize_name` + `ManifestParser` protocol).
- `pyreach/exceptions.py` updated with `PyReachError`, `ConfigError`, `ParseError`, `OSVError`.
- `tests/unit/parsers/test_manifest_contract.py`.
- Signed-off MR.

## Acceptance Criteria

- Interface reviewed by Alonso; documented in docstrings. ✅ (roadmap S1-T1)
- `Dependency` matches spec §3.1 field-for-field.
- All contract tests pass.
- `ruff` and `mypy` clean on the new files.

## Verification

```bash
poetry run pytest tests/unit/parsers/test_manifest_contract.py -q
poetry run ruff check pyreach/parsers/manifest.py pyreach/exceptions.py
poetry run mypy pyreach/parsers/manifest.py
```

## Edge Cases & Pitfalls

- Do **not** make `Dependency` mutable "for convenience" — downstream code relies on hashing.
- `Optional` defaults must come after required fields in the dataclass.
- Keep `normalize_name` pure and dependency-free; `packaging.utils.canonicalize_name` may be
  used instead but then document the dependency.
- `Protocol` with `runtime_checkable` only checks method *presence*, not signatures — tests
  should still assert behavior.

## Risks / Scope Cuts

- **R7 (AST complexity)** is not affected; no cut needed.
- If `Protocol` support is problematic on CI's Python version, fall back to
  `abc.ABC` with `@abstractmethod` (document the change).

## Definition of Done

- [ ] `Dependency` and `ManifestParser` merged to `main`.
- [ ] Contract tests green in CI (may be added in S1-T7).
- [ ] Alonso's review recorded.
- [ ] Docstrings explain the version-normalization and no-execution rules.
