"""Fixtures for AST engine tests.

These fixtures build upon the base fixtures in tests/conftest.py and are designed
to be consumed by S2 (AST engine) and S3 (Call-graph engine) tests.
"""

import ast
from pathlib import Path

import pytest

from pyreach.ast.builder import ASTBuilder, ModuleAST
from pyreach.ast.resolver import ModuleIndex
from pyreach.ast.symbols import SymbolTableBuilder


@pytest.fixture
def module_ast_factory():
    """Builds a ModuleAST from a source string."""

    def _factory(source: str, fqn: str) -> ModuleAST:
        tree = ast.parse(source)
        return ModuleAST(
            file_path="dummy.py",
            module_fqn=fqn,
            tree=tree,
        )

    return _factory


@pytest.fixture
def module_index_from_dir():
    """Builds a ModuleIndex from all Python files in a directory."""

    def _factory(path: Path) -> ModuleIndex:
        builder = ASTBuilder(module_root=path)
        source_files = list(path.rglob("*.py"))

        modules = []
        for sf in source_files:
            mod = builder.build_file(sf)
            if mod:
                modules.append(mod)

        index = ModuleIndex(modules)

        # Run symbol resolution for each module
        for mod in modules:
            sym_builder = SymbolTableBuilder(mod, index.get)
            sym_builder.build()

        return index

    return _factory


@pytest.fixture
def opened_project(tmp_path: Path) -> Path:
    """Copies the code_samples fixture project to tmp_path for mutation testing."""
    import shutil

    real_project_root = Path(__file__).resolve().parent.parent.parent.parent
    src = real_project_root / "tests" / "fixtures" / "code_samples"
    dst = tmp_path / "code_samples"
    shutil.copytree(src, dst)
    return dst
