"""Import resolution for the PyReach AST engine.

``ModuleIndex`` indexes parsed modules by fully-qualified name and supports
symbol lookups across module boundaries. ``ImportResolver`` uses an index
to resolve attribute chains (e.g. ``requests.get``) to their defining
FQNs with a confidence score.
"""

import ast
import builtins
from collections.abc import Iterable
from dataclasses import dataclass

from pyreach.ast.builder import ModuleAST


@dataclass
class ResolvedTarget:
    fqn: str
    confidence: float
    resolved: bool


class ModuleIndex:
    def __init__(self, modules: Iterable[ModuleAST]) -> None:
        self._modules = {mod.module_fqn: mod for mod in modules}

    def get(self, fqn: str) -> ModuleAST | None:
        return self._modules.get(fqn)

    def find_symbol(self, fqn: str) -> str | None:
        """Resolve a fully-qualified name to the module that defines it.

        Two-step lookup: find the longest module prefix, then look up the
        remaining attribute chain in that module's symbol table.
        """
        if fqn in self._modules:
            return fqn

        parts = fqn.split(".")
        for i in range(len(parts), 0, -1):
            mod_fqn = ".".join(parts[:i])
            if mod_fqn not in self._modules:
                continue

            attr_chain = parts[i:]
            if not attr_chain:
                return mod_fqn

            mod = self._modules[mod_fqn]
            current: ModuleAST | None = mod
            current_fqn = mod_fqn
            for sym in attr_chain:
                if current is None:
                    return None
                if sym in current.symbol_table:
                    current_fqn = current.symbol_table[sym]
                    current = self.get(current_fqn)
                    if current is None:
                        return current_fqn
                else:
                    return None
            return current_fqn

        return None

    def has_module_prefix(self, fqn: str) -> bool:
        parts = fqn.split(".")
        for i in range(len(parts), 0, -1):
            if ".".join(parts[:i]) in self._modules:
                return True
        return False


class ImportResolver:
    def __init__(self, index: ModuleIndex) -> None:
        self.index = index

    @staticmethod
    def _is_top_level_binding(name: str, module: ModuleAST) -> bool:
        tree = module.tree
        if not isinstance(tree, ast.Module):
            return False
        return any(
            isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and stmt.name == name
            for stmt in tree.body
        )

    def resolve_name(self, name: str, module: ModuleAST) -> str | None:
        if name in module.symbol_table:
            return module.symbol_table[name]

        if self._is_top_level_binding(name, module):
            return f"{module.module_fqn}.{name}"

        if hasattr(builtins, name):
            return name

        return None

    def resolve_method_chain(
        self, chain: list[str], class_fqn: str | None = None
    ) -> ResolvedTarget:
        """Delegate a ``self``/``cls`` attribute chain to method resolution.

        With a *class_fqn* (supplied by S3-T4) maps ``self.other`` to
        ``<Class>.other``. Without one, returns the raw chain at medium
        confidence so the call stays conservatively classified.
        """
        if class_fqn and len(chain) > 1:
            fqn = ".".join([class_fqn] + chain[1:])
            return ResolvedTarget(fqn, 0.5, False)
        return ResolvedTarget(".".join(chain), 0.5, False)

    def resolve_chain(self, chain: list[str], module: ModuleAST) -> ResolvedTarget:
        if not chain:
            return ResolvedTarget("", 0.0, False)

        base = chain[0]

        if base in ("self", "cls"):
            return self.resolve_method_chain(chain)

        if base not in module.symbol_table and hasattr(builtins, base):
            return ResolvedTarget(".".join(chain), 0.0, False)

        resolved_base = self.resolve_name(base, module)

        if resolved_base:
            if len(chain) == 1:
                return ResolvedTarget(resolved_base, 1.0, True)

            candidate_fqn = f"{resolved_base}.{'.'.join(chain[1:])}"

            found_fqn = self.index.find_symbol(candidate_fqn)
            if found_fqn:
                return ResolvedTarget(found_fqn, 1.0, True)

            if self.index.has_module_prefix(candidate_fqn):
                return ResolvedTarget(candidate_fqn, 0.5, False)

            return ResolvedTarget(candidate_fqn, 0.0, False)

        fqn = ".".join(chain)
        if self.index.has_module_prefix(fqn):
            return ResolvedTarget(fqn, 0.5, False)

        return ResolvedTarget(fqn, 0.0, False)

    @staticmethod
    def extract_attribute_chain(node: ast.AST) -> list[str]:
        chain: list[str] = []
        current: ast.AST | None = node
        while current:
            if isinstance(current, ast.Attribute):
                chain.insert(0, current.attr)
                current = current.value
            elif isinstance(current, ast.Name):
                chain.insert(0, current.id)
                current = None
            else:
                return []
        return chain
