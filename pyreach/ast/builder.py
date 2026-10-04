"""AST parsing, module FQN computation, and ModuleAST wrapper."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pyreach.exceptions import ParseError

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from pyreach.loaders.source import SourceFile

logger = logging.getLogger(__name__)


def parse_source(file_path: str, source_text: str) -> ast.AST:
    """Parse Python source code into an AST without execution.

    Raises:
        ParseError: If the source code contains syntax errors or null bytes.
    """
    try:
        return ast.parse(source_text, filename=file_path, mode="exec")
    except SyntaxError as exc:
        raise ParseError(f"Syntax error in {file_path}:{exc.lineno}: {exc.msg}") from exc
    except (ValueError, UnicodeDecodeError) as exc:
        raise ParseError(f"Failed to decode or parse {file_path}: {exc}") from exc


def compute_module_fqn(
    file_path: Path,
    module_root: Path,
    package_root: Path | None = None,
) -> str:
    """Compute the fully qualified module name (FQN) from a file path and module root.

    Examples:
        - ``myapp/utils/http.py`` relative to root -> ``myapp.utils.http``
        - ``requests/__init__.py`` relative to root -> ``requests``
        - ``main.py`` relative to root -> ``main``
        - ``__init__.py`` directly inside the module root -> the root's name

    Raises:
        ValueError: If the file is under neither *module_root* nor *package_root*.
    """
    resolved_file = file_path.resolve()
    resolved_root = module_root.resolve()

    try:
        rel = resolved_file.relative_to(resolved_root)
    except ValueError:
        if package_root is not None:
            resolved_pkg = package_root.resolve()
            rel_to_pkg = resolved_file.relative_to(resolved_pkg)
            parts_list = [package_root.name] + list(rel_to_pkg.with_suffix("").parts)
            if parts_list[-1] == "__init__":
                parts_list = parts_list[:-1]
            return ".".join(parts_list)
        raise

    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]

    if not parts:
        return resolved_root.name

    return ".".join(parts)


@dataclass
class ModuleAST:
    """Canonical container for a parsed module AST and associated symbol tables."""

    file_path: str
    module_fqn: str
    tree: ast.AST
    symbol_table: dict[str, str] = field(default_factory=dict)
    imports: dict[str, str] = field(default_factory=dict)

    def iter_nodes(self) -> Iterator[ast.AST]:
        """Yield all nodes in the AST in breadth-first order (``ast.walk``)."""
        return ast.walk(self.tree)


class ASTBuilder:
    """Orchestrates parsing source files into ModuleAST objects with caching."""

    def __init__(self, module_root: Path, package_root: Path | None = None) -> None:
        self.module_root = module_root.resolve()
        self.package_root = package_root.resolve() if package_root else None
        self._cache: dict[tuple[Path, float], ModuleAST] = {}

    def _is_within_roots(self, resolved: Path) -> bool:
        if self.package_root is not None:
            try:
                resolved.relative_to(self.package_root)
                return True
            except ValueError:
                pass
        try:
            resolved.relative_to(self.module_root)
            return True
        except ValueError:
            return False

    def build_file(self, path: Path) -> ModuleAST | None:
        """Parse a source file and return a ModuleAST, or None on error with a warning.

        Reads are confined to ``module_root`` and ``package_root`` (defense in
        depth on top of :meth:`~pyreach.loaders.source.SourceLoader.discover`).
        """
        resolved = path.resolve()
        if not self._is_within_roots(resolved):
            logger.warning("Refusing to read source file outside module/package roots: %s", path)
            return None

        try:
            mtime = resolved.stat().st_mtime
        except OSError as exc:
            logger.warning("Failed to access source file %s: %s", path, exc)
            return None

        cache_key = (resolved, mtime)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            source_text = resolved.read_text(encoding="utf-8-sig")
            tree = parse_source(str(resolved), source_text)
            fqn = compute_module_fqn(resolved, self.module_root, self.package_root)
            mod_ast = ModuleAST(
                file_path=str(path),
                module_fqn=fqn,
                tree=tree,
            )
            self._cache[cache_key] = mod_ast
            return mod_ast
        except (ParseError, OSError) as exc:
            logger.warning("Failed to parse source file %s: %s", path, exc)
            return None

    def build_all(self, files: Iterable[SourceFile]) -> list[ModuleAST]:
        """Parse all given source files and populate their symbol tables.

        Unparseable files are skipped with warnings.
        """
        results: list[ModuleAST] = []
        skipped = 0
        for sf in files:
            mod_ast = self.build_file(sf.path)
            if mod_ast is not None:
                results.append(mod_ast)
            else:
                skipped += 1

        if skipped > 0:
            logger.info(
                "ASTBuilder completed: %d parsed, %d skipped",
                len(results),
                skipped,
            )

        self._populate_symbol_tables(results)
        return results

    def _populate_symbol_tables(self, modules: list[ModuleAST]) -> None:
        from pyreach.ast.resolver import ModuleIndex
        from pyreach.ast.symbols import SymbolTableBuilder

        index = ModuleIndex(modules)
        for mod in modules:
            SymbolTableBuilder(mod, index.get).build()
