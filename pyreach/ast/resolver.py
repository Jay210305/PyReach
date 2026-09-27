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
        if fqn in self._modules:
            return fqn

        parts = fqn.split(".")
        for i in range(len(parts) - 1, 0, -1):
            mod_fqn = ".".join(parts[:i])
            symbol_path = parts[i:]

            mod = self.get(mod_fqn)
            if mod:
                # Traverse the symbol path within the module
                current_fqn = mod_fqn
                current_mod = mod
                for sym in symbol_path:
                    if sym in current_mod.symbol_table:
                        next_fqn = current_mod.symbol_table[sym]
                        # Continue if another module, but usually one level
                        return next_fqn
                    else:
                        return None  # Symbol not found in this module
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

    def resolve_name(self, name: str, module: ModuleAST) -> str | None:
        if name in module.symbol_table:
            return module.symbol_table[name]

        # Check builtins
        if hasattr(builtins, name):
            return name

        return None

    def resolve_chain(self, chain: list[str], module: ModuleAST) -> ResolvedTarget:
        if not chain:
            return ResolvedTarget("", 0.0, False)

        base = chain[0]

        if base == "self" or base == "cls":
            # Delegate to method resolution in S3-T4
            fqn = ".".join(chain)
            return ResolvedTarget(fqn, 0.5, False)

        resolved_base = self.resolve_name(base, module)

        if resolved_base:
            # It's in the symbol table or builtins
            if len(chain) == 1:
                return ResolvedTarget(resolved_base, 1.0, True)

            candidate_fqn = f"{resolved_base}.{'.'.join(chain[1:])}"

            found_fqn = self.index.find_symbol(candidate_fqn)
            if found_fqn:
                return ResolvedTarget(found_fqn, 1.0, True)

            if self.index.has_module_prefix(candidate_fqn):
                return ResolvedTarget(candidate_fqn, 0.5, False)

            return ResolvedTarget(candidate_fqn, 0.0, False)

        # Unresolved base
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
                # Unsupported node type in chain (e.g. Call)
                return []
        return chain
