# Slice 2 — AST engine

- Scope: `pyreach/ast/ pyreach/loaders/`
- Diff: `git diff c03e073...HEAD -- pyreach/ast pyreach/loaders` (~961 lines)
- Spec: `documentation/implementation/sprint-2-ast-engine/` (S2-T2..T7; T1 is self-study)
- Commits: 1fa7fa9, 32bf44a, e78c558, de80c37
- Date: 2026-10-02

## Standards

### Hard violations

1. **`pyreach/ast/resolver.py,cover` (tracked, added in de80c37)** — Confirmed:
   coverage-annotate artifact committed by accident. Violates doc-03 §2 package layout
   (`ast/{__init__,builder,symbols,resolver}.py` only). Fix:
   `git rm "pyreach/ast/resolver.py,cover"`, add `*,cover` to `.gitignore`.
2. **AGENTS.md §11 "no comments unless a non-obvious algorithm demands one"** — multiple
   "what" comments restate the code: `symbols.py:28` (`# Populate module dicts`),
   `symbols.py:70` (`# level is 0 for absolute…` — restates stdlib), `symbols.py:98,103`
   (`# Determine names to import`, `# Look for __all__`), `builder.py:67`,
   `resolver.py:41` (duplicates its own docstring), `resolver.py:86` (`# Check builtins`),
   `packages.py:61`. Delete or fold into docstrings.
3. **AGENTS.md §11 "confine file reads to project root and resolved site-packages"** —
   `builder.py:96-110`: `build_file()` resolves and reads *any* path handed to it;
   containment is only enforced in `SourceLoader.discover` (`source.py:76`). Builder is
   the component doing the read, so the guard belongs there (defense in depth). Related
   §12 issue: `builder.py:55` — `relative_to` in the `package_root` branch raises bare
   `ValueError` (not `ParseError`/`PyReachError`) for a file under neither root, escaping
   the `except (ParseError, OSError)` at `builder.py:120`.

### Judgement calls (baseline smells)

- **Duplicated Code** — `packages.py:81-97` vs `99-110`: RECORD-inference and
  `dist.files`-inference are the same shape
  (`if len(parts) >= 2 and parts[1] == "__init__.py": inferred.add(parts[0])`); extract
  one helper. Same in `packages.py:154-168`: the Windows and lowercase-layout blocks
  differ only in the dir name — loop over candidates. Also `builder.py:110`
  re-implements the read in `source.py:92-103` (`SourceLoader.read` is dead from the
  builder's perspective) with divergent error semantics (raise vs warn+None).
- **Nit:** `symbols.py:59` — `if drop_count > 0:` is always true (line 52 returns when
  `level == 0`); dead condition.
- **Nit:** `builder.py:84` — docstring "depth-first / breadth-first" is vague and wrong
  (`ast.walk` is BFS); `iter_nodes` is a thin **Middle Man** over `ast.walk`.
- **Nit:** `builder.py:94,105` — mtime-keyed cache never evicts stale entries and hands
  out a shared mutable `ModuleAST` (its `symbol_table` is mutated later by
  `SymbolTableBuilder`).

### Verified compliant

No `eval`/`exec` (only `ast.parse`, `builder.py:28`); per-file `ParseError` → WARNING +
skip + continue (`builder.py:120-122`, §12); PEP 503 via `normalize_name`
(`packages.py:58,128`); iterative traversal (`ast.walk`, `resolver.py:132`); `ModuleAST`
matches §6 contract exactly; py3.10-compatible syntax throughout.

## Spec

### Implemented but wrong

1. **[Critical] Relative imports in `__init__.py` resolve one package level too high** —
   `pyreach/ast/symbols.py:55-60`. `_resolve_level` always drops `level` components from
   `module_fqn`, but for `__init__.py` the FQN *is* the package (builder drops
   `__init__`). So `from .sibling import utils` in
   `tests/fixtures/code_samples/relative_pkg/__init__.py:1` yields `utils →
   sibling.utils` instead of `relative_pkg.sibling.utils` — real bug in-repo, masked
   because `test_relative_package_imports` only checks `main.py`. Spec: "Compute the
   absolute base module from `level` and `ModuleAST.module_fqn`" (S2-T5 §5.3). This also
   undermines S2-T6's acceptance "resolves `requests.get` to `requests.api.get`", since
   re-exports live in `__init__.py`; `test_resolver.py:15` bypasses it ("Mocking
   SymbolTableBuilder's behavior").
2. **[Improvement] `resolve_name` lacks the local-binding fallback** —
   `pyreach/ast/resolver.py:82-90`. Spec §6.2: "If it is a top-level binding (e.g. a
   function defined in this module), return `f"{module.module_fqn}.{local}"`".
   SymbolTableBuilder records no local defs (`visit_FunctionDef` → pass), so `def f()` →
   `None`; `test_resolve_local_function` passes only via hand-set symbol tables.
3. **[Improvement] `self`/`cls` not delegated to method resolution** —
   `resolver.py:98-101` returns raw `self.other`. Spec §6.3: "delegate to method
   resolution (`<Class>.<attr>`); this is used by S3-T4 and must be exposed as a
   helper". No helper exists; the test even hedges ("Or whatever the spec decides",
   `test_resolver.py:96`).
4. **[Nit] Builtins marked resolved** — spec table wants "`len` with resolved flag
   false"; `resolver.py:107-108` returns `(1.0, True)`, risking spurious STATIC edges
   in S3.

### Missing / partial

5. **[Improvement] No `module_binding` for dotted imports** — `symbols.py:36-49` binds
   only `a → a`. Spec §5.2: "**and** record `module_binding["a.b.c"] = ...` for
   attribute resolution; document the rule" (test admits it, `test_symbols.py:36`).
6. **[Improvement] Production pipeline never populates symbol tables** —
   `builder.py:113-117` leaves them empty; only `tests/unit/ast/conftest.py:49-51` wires
   the builder. S2-T5 DoD: "`ModuleAST.symbol_table` populated by `ASTBuilder`
   pipeline."
7. **[Improvement] PackageResolver gaps** — `packages.py:140-181`: spec §3.4 requires
   check "3. `sys.path` defaults" and "fall back to the current environment with a
   WARNING"; neither exists. `*.egg-link` (§3.3) unhandled (only `direct_url.json`).

### Not asked for

8. **[Improvement] Stray coverage artifact committed** — `pyreach/ast/resolver.py,cover`
   (134 lines); no spec requests it. Remove and gitignore.
9. **[Nit]** `utf-8-sig` vs spec "opens with `encoding="utf-8"`" (`source.py:99`); extra
   defaults `.ruff_cache`/`.eggs` beyond the spec list (`source.py:28-29`); corpus files
   1-8 lines vs "Keep files small (10-40 lines)" (S2-T7 §7.1). All benign/documented.

## Summary

- Standards: 7 findings — worst: accidental `resolver.py,cover` artifact tracked in git
  (plus unguarded file reads in `build_file()`).
- Spec: 9 findings — worst: relative imports in `__init__.py` resolve one package level
  too high (`symbols.py:55-60`), a real bug masked by the test only checking `main.py`.
