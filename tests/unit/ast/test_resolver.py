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


def test_resolve_chain_builtin_not_resolved():
    mod = make_module("", module_fqn="pkg.mod")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["len"], mod)
    assert res.fqn == "len"
    assert res.resolved is False


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
    assert res.confidence == 0.5


def test_resolve_method_chain_with_class():
    mod = make_module("", module_fqn="app.main")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_method_chain(["self", "other"], class_fqn="app.main.Client")
    assert res.fqn == "app.main.Client.other"
    assert res.confidence == 0.5
    assert res.resolved is False


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


def test_find_symbol_fqn_is_module():
    """A FQN that exactly matches a registered module returns itself."""
    mod = make_module("", module_fqn="mypkg")
    index = ModuleIndex([mod])
    assert index.find_symbol("mypkg") == "mypkg"


def test_find_symbol_no_matching_prefix():
    """A FQN with no registered module prefix returns None."""
    mod = make_module("", module_fqn="pkg.mod")
    mod.symbol_table = {"f": "pkg.mod.f"}
    index = ModuleIndex([mod])
    # "other.x.y" shares no prefix with "pkg.mod"
    assert index.find_symbol("other.x.y") is None


def test_find_symbol_symbol_missing_in_module():
    """A FQN whose module prefix exists but symbol is missing returns None."""
    mod = make_module("", module_fqn="pkg")
    mod.symbol_table = {"known": "pkg.known"}
    index = ModuleIndex([mod])
    # "pkg.unknown" — module exists, symbol does not
    assert index.find_symbol("pkg.unknown") is None


def test_find_symbol_chain_spans_modules():
    """A chain that resolves through multiple modules via re-export."""
    # app/main.py: import requests
    app = make_module("import requests", module_fqn="app.main")
    app.symbol_table = {"requests": "requests"}

    # requests/__init__.py: from .core import Session
    req_init = make_module("from .core import Session", module_fqn="requests")
    req_init.symbol_table = {"Session": "requests.core.Session"}

    # requests/core.py: class Session: ...
    req_core = make_module("class Session: pass", module_fqn="requests.core")
    req_core.symbol_table = {"Session": "requests.core.Session"}

    index = ModuleIndex([app, req_init, req_core])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["requests", "Session"], app)
    assert res.fqn == "requests.core.Session"
    assert res.confidence == 1.0


def test_find_symbol_chain_module_not_in_index():
    """A chain whose resolved target is not in the index returns the FQN."""
    mod = make_module("import foo", module_fqn="app.main")
    mod.symbol_table = {"foo": "foo"}
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    # "foo.Bar" resolves to "foo.Bar" but "foo" is in the index,
    # "foo.Bar" is not — current becomes None after lookup
    res = resolver.resolve_chain(["foo", "Bar"], mod)
    assert res.fqn == "foo.Bar"
    assert res.confidence == 0.0


def test_resolve_chain_empty_list():
    """An empty chain returns an unresolved target."""
    mod = make_module("", module_fqn="app.main")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)
    res = resolver.resolve_chain([], mod)
    assert res.fqn == ""
    assert res.confidence == 0.0
    assert res.resolved is False


def test_resolve_chain_has_module_prefix_but_unresolved():
    """A chain whose FQN has a module prefix but symbol is not found."""
    mod = make_module("", module_fqn="app.main")
    index = ModuleIndex([mod])
    resolver = ImportResolver(index)

    res = resolver.resolve_chain(["unknown", "foo"], mod)
    assert res.fqn == "unknown.foo"
    assert res.confidence == 0.0
    assert res.resolved is False


def test_extract_attribute_chain_unsupported_node():
    """A Call node in the chain returns an empty list."""
    source = "func()"
    tree = ast.parse(source)
    call_node = cast(ast.Call, tree.body[0])
    chain = ImportResolver.extract_attribute_chain(call_node)
    assert chain == []


def test_extract_attribute_chain_nested_attribute():
    """A deeply nested attribute chain extracts all names."""
    source = "a.b.c.d"
    tree = ast.parse(source)
    expr = cast(ast.Expr, tree.body[0])
    chain = ImportResolver.extract_attribute_chain(expr.value)
    assert chain == ["a", "b", "c", "d"]


def test_has_module_prefix_true():
    mod = make_module("", module_fqn="pkg.sub")
    index = ModuleIndex([mod])
    assert index.has_module_prefix("pkg.sub.foo.bar") is True
    assert index.has_module_prefix("pkg.sub") is True


def test_has_module_prefix_false():
    mod = make_module("", module_fqn="pkg.sub")
    index = ModuleIndex([mod])
    assert index.has_module_prefix("other.foo") is False
    assert index.has_module_prefix("") is False
