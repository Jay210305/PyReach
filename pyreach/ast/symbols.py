import ast
from dataclasses import dataclass
from typing import Callable, Literal

from pyreach.ast.builder import ModuleAST


@dataclass
class SymbolEntry:
    local_name: str
    fqn: str
    kind: Literal["module", "class", "function", "name", "star"]
    import_node: ast.AST | None = None


class SymbolTableBuilder(ast.NodeVisitor):
    def __init__(self, module: ModuleAST, loader: Callable[[str], ModuleAST | None]) -> None:
        self.module = module
        self.loader = loader
        self.symbols: dict[str, SymbolEntry] = {}
        self._visited_modules: set[str] = set()

    def build(self) -> dict[str, str]:
        self._visited_modules.add(self.module.module_fqn)
        self.visit(self.module.tree)

        # Populate module dicts
        self.module.symbol_table = {name: entry.fqn for name, entry in self.symbols.items()}
        for name, entry in self.symbols.items():
            if entry.kind in ("module", "name", "star"):
                self.module.imports[name] = entry.fqn

        return self.module.symbol_table

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.asname:
                self.symbols[alias.asname] = SymbolEntry(
                    local_name=alias.asname, fqn=alias.name, kind="module", import_node=node
                )
            else:
                top_level_name = alias.name.split(".")[0]
                self.symbols[top_level_name] = SymbolEntry(
                    local_name=top_level_name,
                    fqn=top_level_name,  # By design, a->a
                    kind="module",
                    import_node=node,
                )

    def _resolve_level(self, level: int, module: str | None) -> str:
        if level == 0:
            return module or ""

        parts = self.module.module_fqn.split(".")
        if self.module.module_fqn:
            # drop `level` trailing parts from the current module's FQN
            drop_count = level
            if drop_count > 0:
                parts = parts[:-drop_count] if drop_count < len(parts) else []
            base = ".".join(parts)
        else:
            base = ""

        if module:
            return f"{base}.{module}" if base else module
        return base

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # level is 0 for absolute, >0 for relative
        base_module = self._resolve_level(node.level, node.module)

        for alias in node.names:
            if alias.name == "*":
                self._handle_star_import(base_module, node)
                continue

            local_name = alias.asname or alias.name
            fqn = f"{base_module}.{alias.name}" if base_module else alias.name

            self.symbols[local_name] = SymbolEntry(
                local_name=local_name, fqn=fqn, kind="name", import_node=node
            )

    def _handle_star_import(self, base_module: str, node: ast.ImportFrom) -> None:
        if base_module in self._visited_modules:
            return  # Circular import detected

        target_mod = self.loader(base_module)
        if not target_mod:
            self.symbols["*"] = SymbolEntry(
                local_name="*", fqn=f"{base_module}.*", kind="star", import_node=node
            )
            return

        self._visited_modules.add(base_module)

        # Determine names to import
        exported_names: list[str] = []
        has_all = False

        if isinstance(target_mod.tree, ast.Module):
            # Look for __all__
            for stmt in target_mod.tree.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(stmt.value, (ast.List, ast.Tuple)):
                                for elt in stmt.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        exported_names.append(elt.value)
                                has_all = True

            if not has_all:
                # Fallback heuristic
                for stmt in target_mod.tree.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not stmt.name.startswith("_"):
                            exported_names.append(stmt.name)
                    elif isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                if not target.id.startswith("_"):
                                    exported_names.append(target.id)

        for name in exported_names:
            self.symbols[name] = SymbolEntry(
                local_name=name, fqn=f"{base_module}.{name}", kind="star", import_node=node
            )

        self._visited_modules.remove(base_module)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
            # simple alias: Client = requests.Session
            # value is requests.Session -> base is requests
            base_name = node.value.value.id
            if base_name in self.symbols:
                base_fqn = self.symbols[base_name].fqn
                attr_name = node.value.attr
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.symbols[target.id] = SymbolEntry(
                            local_name=target.id, fqn=f"{base_fqn}.{attr_name}", kind="name"
                        )

        self.generic_visit(node)

    # Don't descend into function or class bodies unless they are at module scope?
    # Wait, the node visitor by default descends into everything if we call generic_visit.
    # To ONLY walk module scope for imports, we should override FunctionDef/ClassDef to do nothing.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass  # Do not descend

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass  # Do not descend

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        pass  # Do not descend
