# S2-T1 — AST module self-study (Mitigation M1)

| Field | Value |
|-------|-------|
| Sprint | 2 — AST Syntactic Engine and Alias Resolution |
| Owner | Julio Centeno |
| Effort | 16 h (2 days) |
| Dependencies | None within Sprint 2 (front-loaded; can begin during Sprint 1 buffer) |
| Related docs | `06-ast-and-callgraph-engine.md` §1; `10-risk-and-contingency-plan.md` §2 R7, §3 |

## Purpose

De-risk the whole AST engine by mastering CPython's `ast` module **before** writing
production code. Risk **R7** states that AST complexity is the most likely source of Sprint
2/3 slippage; this task is the mandated mitigation M1. Its output is knowledge codified as
notes and a reusable traversal cheat-sheet, not shipped features.

## Preconditions

- Python 3.10+ REPL available.
- Access to `06-ast-and-callgraph-engine.md` and the official `ast` docs.
- A sample corpus of Python files to inspect (use the stdlib `Lib/` directory and snippets
  from `requests`, `flask`).

## Essential Sub-tasks

### 1.1 Study AST node taxonomy (3 h)

- Read the `ast` module docs and `ast.dump` output for representative files.
- Produce a table of node types relevant to PyReach: `Module`, `Import`, `ImportFrom`,
  `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, `Call`, `Attribute`, `Name`, `Lambda`,
  `Assign`, `AnnAssign`, `Return`, `Await`, `Decorator`.
- For each, note: how to detect it, how to access its fields, and whether it creates a call
  graph node or edge.

### 1.2 Practice traversal patterns (3 h)

Write throwaway scripts (kept under `docs/study/` or a scratch branch) that:

1. Extract all function/class names from a directory using `ast.walk` vs recursive `NodeVisitor`.
2. Print line numbers for every `ast.Call`, including nested calls.
3. Handle `AsyncFunctionDef` identically to `FunctionDef`.
4. Distinguish `ast.Name` (`foo()`) from `ast.Attribute` (`obj.foo()`).
5. Extract decorators (`decorator_list`) and their call arguments.
6. Parse `if __name__ == "__main__":` blocks and list statements inside.

### 1.3 Study imports and relative packages (3 h)

- Learn the difference between `ast.Import` (`import a.b`) and `ast.ImportFrom`
  (`from a import b`), including `level` for relative imports (`from . import x` has `level=1`).
- Determine how to compute FQNs from file paths (see `06-...md` §1.2) and test the algorithm
  on stdlib packages.
- Understand `__init__.py` semantics and namespace packages (PEP 420), even if only partially
  supported.

### 1.4 Study syntax errors and recovery (2 h)

- Catalog `SyntaxError` attributes (`lineno`, `offset`, `msg`, `filename`).
- Decide handling: skip file with a WARNING (never abort the scan) per spec §8.
- Test on malformed files, encoding errors (`SyntaxError` for bad source encoding), and
  f-strings requiring newer grammar.

### 1.5 Study edge cases that affect later tasks (3 h)

Document findings for S2-T4..T6 and S3:

- Nested functions and closures (what FQN do they get?).
- Methods defined inside classes nested in functions.
- `global`/`nonlocal` and name shadowing.
- Conditional imports (`try: import x except ImportError:`).
- Aliased decorators and callable class instances.
- Type hints referencing imported names (should not become call edges).

### 1.6 Produce the AST notes document (2 h)

Create `documentation/study/ast-notes.md` (internal, not user-facing) containing:

- The node taxonomy table from 1.1.
- The traversal comparisons and code snippets from 1.2.
- The FQN algorithm verified against examples.
- A "gotchas" list consumed by implementation tasks.
- A self-assessment checklist proving the roadmap criterion:
  *"Can manually traverse and classify all node types in sample files."*

## Deliverables

- `documentation/study/ast-notes.md` (or `docs/ast-notes.md`).
- Optional scratch scripts under `scripts/study/`.
- A short demo in the daily/weekly sync showing traversal of a real library file.

## Acceptance Criteria

- Can manually traverse and classify all node types in sample files. ✅ (roadmap S2-T1)
- Notes include verified FQN examples (`src/myapp/utils/http.py -> myapp.utils.http`).
- Implementation tasks S2-T4..T6 can cite a specific note section for each algorithm.

## Verification

- Peer walkthrough: explain `ast.dump` output of a snippet containing imports, a class,
  methods, `self` calls, a lambda, and an `if __name__` block.
- Verify the FQN algorithm on at least 10 real files without errors.

## Edge Cases & Pitfalls

- `ast.walk` yields nodes in breadth-first order but loses parent context; use a `NodeVisitor`
  when the parent matters (e.g., associating a `Call` with its enclosing function).
- `ast.dump(..., include_attributes=True)` needed to see `lineno`/`col_offset`.
- `node.lineno` may not exist on all node types (e.g., `arguments`); use `getattr`.
- Windows path separators must not leak into module FQNs.

## Risks / Scope Cuts

- **R7**: if this study reveals import resolution is infeasible, invoke the simplification
  fallback early: support only absolute imports + simple relative imports; defer star imports
  (see `10-risk-and-contingency-plan.md` §2 R7, §3).

## Definition of Done

- [ ] Notes committed and reviewed by Alonso.
- [ ] FQN algorithm validated on 10+ files.
- [ ] Gotchas list referenced by S2-T4/T5/T6 PRs.
- [ ] Confidence checklist signed off before S2-T4 starts.
