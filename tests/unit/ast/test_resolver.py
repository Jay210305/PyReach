import ast
from typing import cast

from pyreach.ast.builder import ModuleAST

# These classes will be implemented in pyreach.ast.resolver
from pyreach.ast.resolver import ImportResolver, ModuleIndex


def make_module(source: str, module_fqn: str = "test_pkg.test_mod") -> ModuleAST:
    tree = ast.parse(source)
    mod = ModuleAST(
        file_path="dummy.py", module_fqn=module_fqn, tree=tree, symbol_table={}, imports={}
    )
    # Mocking SymbolTableBuilder's behavior for testing purposes
    # Alternatively, we could actually run SymbolTableBuilder here
    return mod


def test_resolve_local_function():
    mod = make_module("def f(): pass", module_fqn="pkg.mod")
    mod.symbol_table = {"f": "pkg.mod.f"}

    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_name("f", mod)
    assert res == "pkg.mod.f"


def test_resolve_builtin():
    mod = make_module("", module_fqn="pkg.mod")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_name("len", mod)
    assert res == "len"


def test_extract_attribute_chain():
    source = "a.b.c()"
    tree = ast.parse(source)
    call_node = cast(ast.Call, cast(ast.Expr, tree.body[0]).value)

    chain = ImportResolver.extract_attribute_chain(call_node.func)
    assert chain == ["a", "b", "c"]


def test_resolve_alias_call():
    mod = make_module("import numpy as np", module_fqn="app.main")
    mod.symbol_table = {"np": "numpy"}

    numpy_mod = make_module("def array(): pass", module_fqn="numpy")
    numpy_mod.symbol_table = {"array": "numpy.array"}

    index = ModuleIndex([mod, numpy_mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["np", "array"], mod)
    assert res.fqn == "numpy.array"
    assert res.confidence == 1.0


def test_resolve_from_import():
    mod = make_module("from x import y", module_fqn="app.main")
    mod.symbol_table = {"y": "x.y"}

    x_mod = make_module("def y(): pass", module_fqn="x")
    x_mod.symbol_table = {"y": "x.y"}

    index = ModuleIndex([mod, x_mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["y"], mod)
    assert res.fqn == "x.y"
    assert res.confidence == 1.0


def test_unresolved_chain():
    mod = make_module("", module_fqn="app.main")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["unknown", "foo"], mod)
    assert res.fqn == "unknown.foo"
    assert res.confidence == 0.0


def test_self_method():
    mod = make_module("", module_fqn="app.main")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["self", "other"], mod)
    assert res.fqn == "self.other"
    assert res.confidence == 0.5  # Or whatever the spec decides for low confidence


def test_resolve_imported_call_re_export():
    mod = make_module("import requests", module_fqn="app.main")
    mod.symbol_table = {"requests": "requests"}

    # requests/__init__.py
    req_init = make_module("from .api import get", module_fqn="requests")
    req_init.symbol_table = {"get": "requests.api.get"}

    # requests/api.py
    req_api = make_module("def get(): pass", module_fqn="requests.api")
    req_api.symbol_table = {"get": "requests.api.get"}

    index = ModuleIndex([mod, req_init, req_api])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["requests", "get"], mod)
    assert res.fqn == "requests.api.get"
    assert res.confidence == 1.0
