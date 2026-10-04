import ast
from pathlib import Path

from pyreach.ast.builder import ASTBuilder
from pyreach.ast.resolver import ImportResolver


def test_requests_snippet_symbols(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("requests_snippet")
    assert mod is not None
    assert "requests" in mod.symbol_table

    resolver = ImportResolver(index)
    res = resolver.resolve_chain(["requests", "get"], mod)
    assert res.fqn == "requests.get"


def test_flask_routes_discovered(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("flask_snippet")
    assert mod is not None
    funcs = [node for node in mod.iter_nodes() if isinstance(node, ast.FunctionDef)]
    assert len(funcs) == 1
    assert funcs[0].name == "index"
    assert len(funcs[0].decorator_list) == 1


def test_fastapi_async_handlers(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("fastapi_snippet")
    assert mod is not None
    async_funcs = [node for node in mod.iter_nodes() if isinstance(node, ast.AsyncFunctionDef)]
    assert len(async_funcs) == 1
    assert async_funcs[0].name == "root"


def test_relative_package_imports(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("relative_pkg.main")
    assert mod is not None
    assert "sibling" in mod.symbol_table
    assert mod.symbol_table["sibling"] == "relative_pkg.sibling"

    resolver = ImportResolver(index)
    res = resolver.resolve_chain(["sibling", "utils"], mod)
    assert res.fqn == "relative_pkg.sibling.utils"


def test_relative_package_init_imports(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    init_mod = index.get("relative_pkg")
    assert init_mod is not None
    assert "utils" in init_mod.symbol_table
    assert init_mod.symbol_table["utils"] == "relative_pkg.sibling.utils"


def test_star_import_names(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("star_import")
    assert mod is not None
    assert "*" in mod.symbol_table
    assert mod.symbol_table["*"] == "math.*"


def test_dynamic_patterns_detected(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("dynamic_patterns")
    assert mod is not None
    calls = [node for node in mod.iter_nodes() if isinstance(node, ast.Call)]
    call_names = [node.func.id for node in calls if isinstance(node.func, ast.Name)]
    assert "eval" in call_names
    assert "exec" in call_names
    assert "getattr" in call_names


def test_inheritance_parsed(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("inheritance")
    assert mod is not None
    classes = [node for node in mod.iter_nodes() if isinstance(node, ast.ClassDef)]
    assert len(classes) == 2
    derived = next(c for c in classes if c.name == "Derived")
    assert len(derived.bases) == 1
    assert derived.bases[0].id == "Base"


def test_syntax_error_skipped(opened_project: Path, module_index_from_dir):
    index = module_index_from_dir(opened_project)
    mod = index.get("syntax_error")
    assert mod is None


def test_no_crashes_on_corpus(opened_project: Path):
    builder = ASTBuilder(module_root=opened_project)
    files = list(opened_project.rglob("*.py"))
    for f in files:
        builder.build_file(f)
