"""Entry point auto-detection and override merging (S3-T7).

Entry points are the roots of reachability. If none are found, every symbol
becomes ``NOT_REACHABLE`` — a catastrophic false-negative source — so the
detector errs toward over-detection (R2: extra roots only make the analysis
more conservative, never less).

Detection rules (union, deterministically sorted):

1. Top-level function named ``main`` -> ``<module>.main``.
2. ``if __name__ == "__main__":`` block -> synthetic ``<module>.__main__`` root
   plus functions called directly inside the block.
3. Framework decorators:
   - FastAPI/Starlette: ``@app.get``/``.post``/``.put``/``.delete``/``.patch``
     on an ``app``/``router``/``api`` binding.
   - Flask: ``@x.route`` (any binding).
   - Django: not auto-detected (too diverse); rely on ``-e``.
4. Module-level ``asyncio.run(...)`` / ``uvicorn.run(...)`` -> module root plus
   the referenced callable.

``console_scripts`` from ``pyproject.toml``/``setup.py`` is a documented
best-effort follow-up; it is not implemented here.
"""

from __future__ import annotations

import ast
import logging
from collections.abc import Iterable

from pyreach.ast.builder import ModuleAST
from pyreach.exceptions import ConfigError

logger = logging.getLogger(__name__)

_FASTAPI_METHODS = frozenset({"get", "post", "put", "delete", "patch"})
_FASTAPI_BINDINGS = frozenset({"app", "router", "api"})
_FLASK_METHODS = frozenset({"route"})
_RUNNER_FQNS = frozenset({"asyncio.run", "uvicorn.run"})

_NO_ENTRY_POINTS_MSG = "No entry points detected. Use -e to specify entry points explicitly."


def _fqn(module_fqn: str, *parts: str) -> str:
    base = [module_fqn] if module_fqn else []
    return ".".join(base + [p for p in parts if p])


def _attr_chain(node: ast.AST) -> list[str]:
    """Flatten ``obj.method`` / ``pkg.sub.func`` into ``["obj", "method"]``."""
    chain: list[str] = []
    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.Attribute):
            chain.append(current.attr)
            current = current.value
        elif isinstance(current, ast.Name):
            chain.append(current.id)
            current = None
        else:
            return []
    return list(reversed(chain))


def _decorator_chain(decorator: ast.AST) -> list[str]:
    if isinstance(decorator, ast.Name):
        return [decorator.id]
    if isinstance(decorator, ast.Attribute):
        return _attr_chain(decorator)
    if isinstance(decorator, ast.Call):
        return _decorator_chain(decorator.func)
    return []


def _is_framework_decorator(decorator: ast.AST) -> bool:
    chain = _decorator_chain(decorator)
    if len(chain) < 2:
        return False
    method = chain[-1]
    binding = chain[-2]
    if method in _FASTAPI_METHODS:
        return binding in _FASTAPI_BINDINGS
    return method in _FLASK_METHODS


def _is_main_block(node: ast.If) -> bool:
    test = node.test
    if not (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)):
        return False
    if test.left.id != "__name__" or len(test.ops) != 1 or len(test.comparators) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    comparator = test.comparators[0]
    # ast.Constant normalizes both 'single' and "double" quotes, so no
    # literal_eval pass is needed on Python 3.10+.
    return isinstance(comparator, ast.Constant) and comparator.value == "__main__"


def _runner_target(call: ast.Call) -> str | None:
    """Return the callable name for ``asyncio.run(main())`` -> ``main``."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Call):
        arg = arg.func
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Attribute):
        chain = _attr_chain(arg)
        return chain[-1] if chain else None
    return None


def _is_runner_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return False
    if isinstance(func, ast.Attribute):
        return ".".join(_attr_chain(func)) in _RUNNER_FQNS
    return False


class _EntryVisitor(ast.NodeVisitor):
    """Collect ``main`` functions and framework-decorated handlers."""

    def __init__(self, module: ModuleAST) -> None:
        self.module = module
        self.entries: set[str] = set()
        self._scope: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node)

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        fqn = _fqn(self.module.module_fqn, *self._scope, node.name)
        if not self._scope and node.name == "main":
            self.entries.add(fqn)
        if any(_is_framework_decorator(d) for d in node.decorator_list):
            self.entries.add(fqn)
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._scope.append(node.name)
        self.generic_visit(node)
        self._scope.pop()


def _detect_module(module: ModuleAST) -> set[str]:
    entries: set[str] = set()

    visitor = _EntryVisitor(module)
    visitor.visit(module.tree)
    entries.update(visitor.entries)

    for stmt in ast.walk(module.tree):
        if isinstance(stmt, ast.If) and _is_main_block(stmt):
            entries.add(_fqn(module.module_fqn, "__main__"))
            for call in ast.walk(stmt):
                if isinstance(call, ast.Call):
                    target = _runner_target(call) if _is_runner_call(call) else _direct_call(call)
                    if target is not None:
                        entries.add(_fqn(module.module_fqn, target))
        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            if _is_runner_call(stmt.value):
                entries.add(_fqn(module.module_fqn, "__main__"))
                target = _runner_target(stmt.value)
                if target is not None:
                    entries.add(_fqn(module.module_fqn, target))

    return entries


def _direct_call(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        chain = _attr_chain(func)
        return chain[-1] if chain else None
    return None


class EntryPointDetector:
    """Auto-detect entry point FQNs from parsed modules."""

    def __init__(self, modules: Iterable[ModuleAST]) -> None:
        self._modules = list(modules)

    def detect(self) -> list[str]:
        entries: set[str] = set()
        for module in self._modules:
            entries.update(_detect_module(module))
        return sorted(entries)


def resolve_entry_points(
    detected: list[str],
    cli_entry_points: list[str],
    config_entry_points: list[str],
    known_fqns: set[str] | None = None,
) -> list[str]:
    """Merge detected and explicitly-configured entry points.

    Precedence is CLI > config > auto-detect, but the result is the union so
    nothing is lost. ``pkg.mod:func`` and ``pkg.mod.func`` are equivalent; the
    ``:`` form is normalized to ``.``. Overrides pointing at an unknown FQN are
    kept with a WARNING (the graph may gain a placeholder node in Sprint 4).
    """
    merged: list[str] = []
    seen: set[str] = set()

    for entry in [*cli_entry_points, *config_entry_points]:
        normalized = entry.replace(":", ".")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
        if known_fqns is not None and normalized not in known_fqns:
            logger.warning("Entry point %s not found in the call graph", normalized)

    for entry in detected:
        if entry not in seen:
            seen.add(entry)
            merged.append(entry)

    return merged


def detect_or_fail(
    modules: Iterable[ModuleAST],
    overrides: list[str] | None = None,
    allow_empty: bool = False,
) -> list[str]:
    """Detect entry points and merge overrides, raising on an empty result.

    Raises ``ConfigError`` when nothing is detected and no override is given,
    so the CLI can surface a clear error instead of a silent ``NOT_REACHABLE``
    storm. ``allow_empty=True`` bypasses the check (used by tests).
    """
    detected = EntryPointDetector(modules).detect()
    resolved = resolve_entry_points(detected, list(overrides or []), [])
    if not resolved and not allow_empty:
        raise ConfigError(_NO_ENTRY_POINTS_MSG)
    return resolved
