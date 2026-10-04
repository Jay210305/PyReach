import ast
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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

        self.module.symbol_table = {name: entry.fqn for name, entry in self.symbols.items()}
        for name, entry in self.symbols.items():
            if entry.kind in ("module", "name", "star"):
                self.module.imports[name] = entry.fqn

        return self.module.symbol_table

    def _is_package_module(self) -> bool:
        return Path(self.module.file_path).name == "__init__.py"

    def _package_fqn(self) -> str:
        """Return the FQN of the package containing this module.

        A package ``__init__.py`` has already been stripped to its package FQN
        by the builder, so its FQN *is* the package. For a regular module the
        package is the FQN minus the trailing module leaf.
        """
        fqn = self.module.module_fqn
        if self._is_package_module():
            return fqn
        if not fqn:
            return ""
        return ".".join(fqn.split(".")[:-1])

    def _resolve_level(self, level: int, module: str | None) -> str:
        if level == 0:
            return module or ""

        package = self._package_fqn()
        parts = package.split(".") if package else []
        drop = level - 1
        if drop > 0:
            parts = parts[:-drop] if drop < len(parts) else []
        base = ".".join(parts)

        if module:
            return f"{base}.{module}" if base else module
        return base

    def visit_Import(self, node: ast.Import) -> None:
        """Bind imported names.

        ``import a.b`` binds only the top-level name ``a`` but also records the
        full dotted path ``a.b`` so attribute chains can be resolved (S2-T5 §5.2).
        """
        for alias in node.names:
            if alias.asname:
                self.symbols[alias.asname] = SymbolEntry(
                    local_name=alias.asname, fqn=alias.name, kind="module", import_node=node
                )
            else:
                top_level = alias.name.split(".")[0]
                self.symbols[top_level] = SymbolEntry(
                    local_name=top_level, fqn=top_level, kind="module", import_node=node
                )
                if "." in alias.name:
                    self.symbols[alias.name] = SymbolEntry(
                        local_name=alias.name, fqn=alias.name, kind="module", import_node=node
                    )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
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
            return

        target_mod = self.loader(base_module)
        if not target_mod:
            self.symbols["*"] = SymbolEntry(
                local_name="*", fqn=f"{base_module}.*", kind="star", import_node=node
            )
            return

        self._visited_modules.add(base_module)

        exported_names: list[str] = []
        has_all = False

        if isinstance(target_mod.tree, ast.Module):
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
                for stmt in target_mod.tree.body:
                    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if not stmt.name.startswith("_"):
                            exported_names.append(stmt.name)
                    elif isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                                exported_names.append(target.id)

        for name in exported_names:
            self.symbols[name] = SymbolEntry(
                local_name=name, fqn=f"{base_module}.{name}", kind="star", import_node=node
            )

        self._visited_modules.remove(base_module)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track simple attribute aliases at module scope.

        Handles ``Name = OtherName.Attribute`` patterns (e.g.
        ``Client = requests.Session``) so the resolver can follow the
        alias to the underlying FQN.

        Intentionally narrow: does not handle ``Name = Name`` renames,
        ``Name = Call()`` results, or chained assignments. Those are
        rare in import/include contexts and are left for a future
        refinement if coverage demands it.
        """
        if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        pass
