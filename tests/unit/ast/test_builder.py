"""Tests for pyreach.ast.builder — ASTBuilder, ModuleAST, compute_module_fqn, parse_source."""

import ast
import logging
from pathlib import Path

import pytest

from pyreach.ast.builder import (
    ASTBuilder,
    ModuleAST,
    compute_module_fqn,
    parse_source,
)
from pyreach.exceptions import ParseError
from pyreach.loaders.source import SourceFile


class TestParseSource:
    def test_parse_valid_source(self) -> None:
        tree = parse_source("test.py", "def foo():\n    return 42\n")
        assert isinstance(tree, ast.Module)
        assert len(tree.body) == 1
        assert isinstance(tree.body[0], ast.FunctionDef)

    def test_parse_syntax_error_raises_parse_error(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            parse_source("bad.py", "def broken(\n")
        assert "bad.py" in str(exc_info.value)
        assert "Syntax error" in str(exc_info.value)

    def test_parse_null_bytes_raises_parse_error(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            parse_source("null.py", "x = 1\x00y = 2")
        assert "null.py" in str(exc_info.value)


class TestComputeModuleFqn:
    def test_compute_module_fqn_standard(self, tmp_path: Path) -> None:
        module_root = tmp_path
        file_path = tmp_path / "myapp" / "utils" / "http.py"
        fqn = compute_module_fqn(file_path, module_root)
        assert fqn == "myapp.utils.http"

    def test_compute_module_fqn_init(self, tmp_path: Path) -> None:
        module_root = tmp_path
        file_path = tmp_path / "myapp" / "__init__.py"
        assert compute_module_fqn(file_path, module_root) == "myapp"

        nested_init = tmp_path / "myapp" / "sub" / "__init__.py"
        assert compute_module_fqn(nested_init, module_root) == "myapp.sub"

    def test_compute_module_fqn_top_level(self, tmp_path: Path) -> None:
        module_root = tmp_path
        file_path = tmp_path / "main.py"
        assert compute_module_fqn(file_path, module_root) == "main"

    def test_compute_module_fqn_with_package_root(self, tmp_path: Path) -> None:
        # e.g., project/src/myapp/core.py with module_root=project/src,
        # package_root=project/src/myapp
        module_root = tmp_path / "src"
        package_root = module_root / "myapp"
        file_path = package_root / "core.py"
        assert compute_module_fqn(file_path, module_root, package_root) == "myapp.core"

    def test_compute_module_fqn_root_init(self, tmp_path: Path) -> None:
        module_root = tmp_path / "mypackage"
        module_root.mkdir()
        file_path = module_root / "__init__.py"
        assert compute_module_fqn(file_path, module_root) == "mypackage"

    def test_compute_module_fqn_outside_module_inside_package(self, tmp_path: Path) -> None:
        other_module_root = tmp_path / "other"
        package_root = tmp_path / "custom_pkg"
        file_path = package_root / "nested" / "mod.py"
        assert (
            compute_module_fqn(file_path, other_module_root, package_root)
            == "custom_pkg.nested.mod"
        )

    def test_compute_module_fqn_outside_all_roots_raises_value_error(self, tmp_path: Path) -> None:
        module_root = tmp_path / "root"
        file_path = tmp_path / "somewhere_else" / "mod.py"
        with pytest.raises(ValueError):
            compute_module_fqn(file_path, module_root)


class TestModuleAST:
    def test_module_ast_fields_and_iter_nodes(self) -> None:
        tree = ast.parse("x = 1\ndef foo(): pass\n")
        mod = ModuleAST(
            file_path="app/test.py",
            module_fqn="app.test",
            tree=tree,
        )
        assert mod.file_path == "app/test.py"
        assert mod.module_fqn == "app.test"
        assert mod.symbol_table == {}
        assert mod.imports == {}

        nodes = list(mod.iter_nodes())
        node_types = {type(n) for n in nodes}
        assert ast.Module in node_types
        assert ast.Assign in node_types
        assert ast.FunctionDef in node_types


class TestASTBuilder:
    def test_build_file_valid(self, tmp_path: Path) -> None:
        root = tmp_path
        py_file = root / "pkg" / "mod.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text("def hello(): pass\n", encoding="utf-8")

        builder = ASTBuilder(module_root=root)
        mod_ast = builder.build_file(py_file)
        assert mod_ast is not None
        assert mod_ast.module_fqn == "pkg.mod"
        assert isinstance(mod_ast.tree, ast.Module)
        assert len(mod_ast.tree.body) == 1

    def test_build_file_syntax_error_returns_none_and_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        root = tmp_path
        bad_file = root / "bad.py"
        bad_file.write_text("def unclosed(\n", encoding="utf-8")

        builder = ASTBuilder(module_root=root)
        with caplog.at_level(logging.WARNING):
            result = builder.build_file(bad_file)
        assert result is None
        assert any("Failed to parse" in record.message for record in caplog.records)
        assert any("bad.py" in record.message for record in caplog.records)

    def test_build_file_nonexistent_returns_none_and_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        root = tmp_path
        missing_file = root / "does_not_exist.py"

        builder = ASTBuilder(module_root=root)
        with caplog.at_level(logging.WARNING):
            result = builder.build_file(missing_file)
        assert result is None
        assert any("Failed to access" in record.message for record in caplog.records)

    def test_build_file_caching(self, tmp_path: Path) -> None:
        root = tmp_path
        py_file = root / "cached_file.py"
        py_file.write_text("value = 123\n", encoding="utf-8")

        builder = ASTBuilder(module_root=root)
        first = builder.build_file(py_file)
        second = builder.build_file(py_file)
        assert first is not None
        assert second is not None
        assert first is second

    def test_build_all_skips_invalid(self, tmp_path: Path) -> None:
        root = tmp_path
        f1 = root / "good1.py"
        f1.write_text("a = 1\n", encoding="utf-8")
        f2 = root / "broken.py"
        f2.write_text("def broken(\n", encoding="utf-8")
        f3 = root / "good2.py"
        f3.write_text("b = 2\n", encoding="utf-8")

        source_files = [
            SourceFile(path=f1, rel_path=Path("good1.py")),
            SourceFile(path=f2, rel_path=Path("broken.py")),
            SourceFile(path=f3, rel_path=Path("good2.py")),
        ]

        builder = ASTBuilder(module_root=root)
        results = builder.build_all(source_files)
        assert len(results) == 2
        fqns = [m.module_fqn for m in results]
        assert "good1" in fqns
        assert "good2" in fqns
        assert "broken" not in fqns

    def test_parses_50_files(self, tmp_path: Path) -> None:
        """Roadmap criterion: parses 50 diverse Python files without syntax errors."""
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()

        source_templates = [
            "def fn_{i}(x: int) -> int:\n    return x + {i}\n",
            "class Cls_{i}:\n    def method(self):\n        return {i}\n",
            "async def afn_{i}():\n    return await other({i})\n",
            "@decorator\ndef deco_{i}():\n    pass\n",
            "lambda_val = lambda x: x * {i}\n",
            "items = [x for x in range({i}) if x % 2 == 0]\n",
            "from math import sqrt as s_{i}\n",
            "import os\nx_{i} = os.getenv('KEY_{i}', 'default')\n",
            "data = {{'key_{i}': {i}, 'other': 'val'}}\n",
            "try:\n    risky_{i}()\nexcept Exception as e:\n    pass\n",
        ]

        source_files: list[SourceFile] = []
        for i in range(50):
            template = source_templates[i % len(source_templates)]
            code = f'"""Module {i} documentation."""\n\n' + template.format(i=i)
            p = corpus_dir / f"sample_{i:02d}.py"
            p.write_text(code, encoding="utf-8")
            source_files.append(SourceFile(path=p, rel_path=Path(f"sample_{i:02d}.py")))

        builder = ASTBuilder(module_root=corpus_dir)
        results = builder.build_all(source_files)
        assert len(results) == 50
        for i, mod in enumerate(results):
            assert mod.module_fqn == f"sample_{i:02d}"
            assert isinstance(mod.tree, ast.Module)
            assert len(list(mod.iter_nodes())) > 0

    def test_build_file_outside_roots_refused(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside.py"
        outside.write_text("x = 1\n", encoding="utf-8")

        builder = ASTBuilder(module_root=root)
        with caplog.at_level(logging.WARNING):
            result = builder.build_file(outside)

        assert result is None
        assert any("outside module/package roots" in record.message for record in caplog.records)

    def test_build_all_populates_symbol_tables(self, tmp_path: Path) -> None:
        root = tmp_path
        (root / "a.py").write_text("import os\n", encoding="utf-8")
        (root / "b.py").write_text("from collections import OrderedDict\n", encoding="utf-8")

        builder = ASTBuilder(module_root=root)
        source_files = [
            SourceFile(path=root / "a.py", rel_path=Path("a.py")),
            SourceFile(path=root / "b.py", rel_path=Path("b.py")),
        ]

        modules = builder.build_all(source_files)
        assert len(modules) == 2

        a_mod = next(m for m in modules if m.module_fqn == "a")
        b_mod = next(m for m in modules if m.module_fqn == "b")
        assert a_mod.symbol_table.get("os") == "os"
        assert b_mod.symbol_table.get("OrderedDict") == "collections.OrderedDict"
