"""Tests for S3-T4 edge extraction — static calls, inheritance, dynamic fallbacks."""

import ast

import networkx as nx

from pyreach.ast.builder import ModuleAST
from pyreach.ast.resolver import ImportResolver, ModuleIndex
from pyreach.callgraph.engine import CallGraphEngine, EdgeExtractor


def _make_module(
    source: str, module_fqn: str, symbol_table: dict[str, str] | None = None
) -> ModuleAST:
    tree = ast.parse(source)
    return ModuleAST(
        file_path=f"{module_fqn.replace('.', '/')}.py",
        module_fqn=module_fqn,
        tree=tree,
        symbol_table=dict(symbol_table or {}),
        imports={},
    )


def _build_graph(modules: list[ModuleAST]) -> nx.DiGraph:
    engine = CallGraphEngine(ModuleIndex(modules))
    return engine.build(modules)


def _edge_data(graph: nx.DiGraph, caller: str, callee: str) -> dict:
    data = graph.get_edge_data(caller, callee)
    assert data is not None, f"missing edge {caller} -> {callee}"
    return data


def test_static_direct_call() -> None:
    utils = _make_module("def helper():\n    pass\n", "utils")
    main = _make_module(
        "from utils import helper\ndef main():\n    helper()\n",
        "main",
        {"helper": "utils.helper"},
    )
    graph = _build_graph([main, utils])
    data = _edge_data(graph, "main.main", "utils.helper")
    assert data["edge_type"] == "STATIC"
    assert data["confidence"] == 1.0


def test_alias_call_edge() -> None:
    numpy = _make_module("def array(data):\n    pass\n", "numpy", {"array": "numpy.array"})
    main = _make_module(
        "import numpy as np\ndef main():\n    np.array([1])\n", "main", {"np": "numpy"}
    )
    graph = _build_graph([main, numpy])
    data = _edge_data(graph, "main.main", "numpy.array")
    assert data["edge_type"] == "STATIC"
    assert data["confidence"] == 1.0


def test_self_method_resolution() -> None:
    mod = _make_module(
        "class Svc:\n"
        "    def run(self):\n"
        "        self.helper()\n"
        "    def helper(self):\n"
        "        pass\n",
        "test",
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.Svc.run", "test.Svc.helper")
    assert data["edge_type"] == "STATIC"


def test_inheritance_edge() -> None:
    mod = _make_module("class Base:\n    pass\nclass Derived(Base):\n    pass\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.Derived", "test.Base")
    assert data["edge_type"] == "INHERITANCE"
    assert data["confidence"] == 1.0


def test_super_call() -> None:
    mod = _make_module(
        "class Base:\n"
        "    def greet(self):\n"
        "        pass\n"
        "class Derived(Base):\n"
        "    def hello(self):\n"
        "        super().greet()\n",
        "test",
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.Derived.hello", "test.Base.greet")
    assert data["edge_type"] == "STATIC"


def test_dynamic_eval_edge() -> None:
    mod = _make_module('def run():\n    eval("1 + 1")\n', "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["edge_type"] == "DYNAMIC"
    assert data["confidence"] == 0.5


def test_unresolved_call_edge() -> None:
    mod = _make_module("def run():\n    mystery()\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<UNRESOLVED>")
    assert data["confidence"] == 0.3


def test_confidence_precedence() -> None:
    mod = _make_module("def f():\n    pass\n", "test")
    engine = CallGraphEngine(ModuleIndex([mod]))
    graph = engine.build([mod])
    extractor = EdgeExtractor(mod, graph, ImportResolver(engine.index))
    extractor._add_edge("test.f", "test.g", "DYNAMIC", 0.5)
    extractor._add_edge("test.f", "test.g", "STATIC", 1.0)
    assert _edge_data(graph, "test.f", "test.g")["edge_type"] == "STATIC"
    extractor._add_edge("test.f", "test.g", "DYNAMIC", 0.5)
    assert _edge_data(graph, "test.f", "test.g")["edge_type"] == "STATIC"


def test_call_attributed_to_enclosing() -> None:
    mod = _make_module(
        "def outer():\n"
        "    def inner():\n"
        "        helper()\n"
        "    return inner\n"
        "def helper():\n"
        "    pass\n",
        "test",
        {"helper": "test.helper"},
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.outer.<locals>.inner", "test.helper")
    assert data["edge_type"] == "STATIC"


def test_importlib_dynamic() -> None:
    mod = _make_module(
        'import importlib\ndef run():\n    importlib.import_module("os")\n',
        "test",
        {"importlib": "importlib"},
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["edge_type"] == "DYNAMIC"


def test_placeholder_node_for_library_call() -> None:
    mod = _make_module(
        "import requests\ndef fetch():\n    requests.get('https://x')\n",
        "test",
        {"requests": "requests"},
    )
    graph = _build_graph([mod])
    assert "test.fetch" in graph.nodes
    data = _edge_data(graph, "test.fetch", "requests.get")
    assert data["edge_type"] == "STATIC"
    assert graph.nodes["requests.get"].get("is_placeholder") is True


def test_recursion_edge() -> None:
    mod = _make_module("def fact(n):\n    return fact(n - 1)\n", "test", {"fact": "test.fact"})
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.fact", "test.fact")
    assert data["edge_type"] == "STATIC"


def test_call_form_decorators() -> None:
    mod = _make_module(
        "@deco()\n@pkg.route('/x')\nclass Svc:\n    pass\n",
        "test",
        {"deco": "test.deco", "pkg": "pkg"},
    )
    graph = _build_graph([mod])
    assert "test.Svc" in graph.nodes
    assert graph.nodes["test.Svc"]["decorators"] == ["deco", "pkg.route"]


def test_attribute_base_class_no_edge() -> None:
    mod = _make_module("import pkg\nclass Derived(pkg.Base):\n    pass\n", "test", {"pkg": "pkg"})
    graph = _build_graph([mod])
    assert "test.Derived" in graph.nodes
    assert graph.get_edge_data("test.Derived", "pkg.Base") is None


def test_default_arg_call_uses_outer_scope() -> None:
    mod = _make_module(
        "def outer():\n"
        "    def f(x=helper()):\n"
        "        pass\n"
        "    return f\n"
        "def helper():\n"
        "    pass\n",
        "test",
        {"helper": "test.helper"},
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.outer", "test.helper")


def test_class_body_call_attributed_to_class() -> None:
    mod = _make_module(
        "@deco\nclass Cfg:\n    value = helper()\ndef helper():\n    pass\n",
        "test",
        {"helper": "test.helper"},
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.Cfg", "test.helper")


def test_instance_var_call() -> None:
    mod = _make_module(
        "class ApiClient:\n"
        "    def fetch(self):\n"
        "        pass\n"
        "def main():\n"
        "    client = ApiClient()\n"
        "    client.fetch()\n",
        "test",
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.main", "test.ApiClient.fetch")
    assert data["edge_type"] == "STATIC"


def test_instance_attr_chain_dynamic() -> None:
    mod = _make_module(
        "class ApiClient:\n"
        "    pass\n"
        "def main():\n"
        "    client = ApiClient()\n"
        "    client.session.get()\n",
        "test",
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.main", "<DYNAMIC>")


def test_non_class_assignment_not_tracked() -> None:
    mod = _make_module(
        "def helper():\n    pass\ndef main():\n    x = helper()\n    x()\n",
        "test",
        {"helper": "test.helper"},
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.main", "test.helper")
    _edge_data(graph, "test.main", "<UNRESOLVED>")


def test_higher_order_call_dynamic() -> None:
    mod = _make_module("def run():\n    factory()()\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["edge_type"] == "DYNAMIC"


def test_imported_but_unparsed_placeholder() -> None:
    mod = _make_module(
        "from lib import thing\ndef run():\n    thing()\n",
        "test",
        {"thing": "lib.thing"},
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "lib.thing")
    assert data["edge_type"] == "STATIC"
    assert graph.nodes["lib.thing"].get("is_placeholder") is True


def test_local_fallback_same_module() -> None:
    mod = _make_module("def run():\n    helper()\ndef helper():\n    pass\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "test.helper")
    assert data["edge_type"] == "STATIC"


def test_star_args_unresolved_dynamic() -> None:
    mod = _make_module("def run(*args):\n    mystery(*args)\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["confidence"] == 0.5


def test_self_attribute_chain_dynamic() -> None:
    mod = _make_module("class Svc:\n    def run(self):\n        self.client.get()\n", "test")
    graph = _build_graph([mod])
    _edge_data(graph, "test.Svc.run", "<DYNAMIC>")


def test_self_outside_class_unresolved() -> None:
    mod = _make_module("def f():\n    self.helper()\n", "test")
    graph = _build_graph([mod])
    _edge_data(graph, "test.f", "<UNRESOLVED>")


def test_nested_in_method_self_resolves() -> None:
    mod = _make_module(
        "class Svc:\n"
        "    def run(self):\n"
        "        def inner():\n"
        "            self.helper()\n"
        "        return inner\n"
        "    def helper(self):\n"
        "        pass\n",
        "test",
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.Svc.run.<locals>.inner", "test.Svc.helper")


def test_self_inherited_from_grandparent() -> None:
    mod = _make_module(
        "class Base:\n"
        "    def foo(self):\n"
        "        pass\n"
        "class Mid(Base):\n"
        "    pass\n"
        "class Leaf(Mid):\n"
        "    def bar(self):\n"
        "        self.foo()\n",
        "test",
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.Leaf.bar", "test.Base.foo")
    assert data["edge_type"] == "STATIC"


def test_super_without_base_unresolved() -> None:
    mod = _make_module("class Lonely:\n    def m(self):\n        super().missing()\n", "test")
    graph = _build_graph([mod])
    _edge_data(graph, "test.Lonely.m", "<UNRESOLVED>")


def test_lambda_body_call() -> None:
    mod = _make_module(
        "def run():\n    return lambda: helper()\ndef helper():\n    pass\n",
        "test",
        {"helper": "test.helper"},
    )
    graph = _build_graph([mod])
    _edge_data(graph, "<lambda>:test.py:2", "test.helper")


def test_module_level_call_skipped() -> None:
    mod = _make_module("helper()\ndef helper():\n    pass\n", "test")
    graph = _build_graph([mod])
    assert graph.get_edge_data("test.helper", "test.helper") is None
    assert graph.number_of_edges() == 0


def test_cross_module_inheritance_via_import() -> None:
    base_mod = _make_module("class Base:\n    pass\n", "m")
    main = _make_module(
        "from m import Base\nclass Derived(Base):\n    pass\n",
        "main",
        {"Base": "m.Base"},
    )
    graph = _build_graph([base_mod, main])
    data = _edge_data(graph, "main.Derived", "m.Base")
    assert data["edge_type"] == "INHERITANCE"


def test_cross_module_attribute_base() -> None:
    pkg = _make_module("class Base:\n    pass\n", "pkg", {"Base": "pkg.Base"})
    main = _make_module("import pkg\nclass Derived(pkg.Base):\n    pass\n", "main", {"pkg": "pkg"})
    graph = _build_graph([pkg, main])
    data = _edge_data(graph, "main.Derived", "pkg.Base")
    assert data["edge_type"] == "INHERITANCE"


def test_factory_result_method_dynamic() -> None:
    mod = _make_module("def run():\n    return factory().method()\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["edge_type"] == "DYNAMIC"


def test_attribute_star_args_dynamic() -> None:
    mod = _make_module("def run(*args):\n    mystery.attr(*args)\n", "test")
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.run", "<DYNAMIC>")
    assert data["confidence"] == 0.5


def test_self_missing_method_unresolved() -> None:
    mod = _make_module(
        "class Svc:\n"
        "    def run(self):\n"
        "        self.missing()\n"
        "    def other(self, *args):\n"
        "        self.gone(*args)\n",
        "test",
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.Svc.run", "<UNRESOLVED>")
    data = _edge_data(graph, "test.Svc.other", "<DYNAMIC>")
    assert data["confidence"] == 0.5


def test_instance_missing_method_fallbacks() -> None:
    mod = _make_module(
        "class C:\n    pass\ndef main(*args):\n    c = C()\n    c.missing()\n    c.other(*args)\n",
        "test",
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.main", "<UNRESOLVED>")
    data = _edge_data(graph, "test.main", "<DYNAMIC>")
    assert data["confidence"] == 0.5


def test_super_star_args_dynamic() -> None:
    mod = _make_module(
        "class Lonely:\n    def m(self, *args):\n        super().missing(*args)\n", "test"
    )
    graph = _build_graph([mod])
    data = _edge_data(graph, "test.Lonely.m", "<DYNAMIC>")
    assert data["confidence"] == 0.5


def test_imported_class_instance_tracked() -> None:
    lib = _make_module("class ApiClient:\n    def fetch(self):\n        pass\n", "lib")
    main = _make_module(
        "from lib import ApiClient\ndef main():\n    c = ApiClient()\n    c.fetch()\n",
        "main",
        {"ApiClient": "lib.ApiClient"},
    )
    graph = _build_graph([lib, main])
    data = _edge_data(graph, "main.main", "lib.ApiClient.fetch")
    assert data["edge_type"] == "STATIC"


def test_diamond_hierarchy_miss_unresolved() -> None:
    mod = _make_module(
        "class A:\n"
        "    pass\n"
        "class B(A):\n"
        "    pass\n"
        "class C(A):\n"
        "    pass\n"
        "class D(B, C):\n"
        "    def m(self):\n"
        "        self.missing()\n",
        "test",
    )
    graph = _build_graph([mod])
    _edge_data(graph, "test.D.m", "<UNRESOLVED>")


def test_metaclass_keyword_visited() -> None:
    mod = _make_module("class C(metaclass=Meta):\n    pass\n", "test")
    graph = _build_graph([mod])
    assert "test.C" in graph.nodes


def test_bare_attribute_decorator() -> None:
    mod = _make_module(
        "@pkg.route\ndef index():\n    pass\n", "test", {"pkg": "pkg", "index": "test.index"}
    )
    graph = _build_graph([mod])
    assert graph.nodes["test.index"]["decorators"] == ["pkg.route"]


def test_inheritance_skips_missing_class_node() -> None:
    from pyreach.callgraph.engine import _build_inheritance_edges

    mod = _make_module("class Base:\n    pass\nclass D(Base):\n    pass\n", "test")
    engine = CallGraphEngine(ModuleIndex([mod]))
    graph = engine.build([mod])
    graph.remove_node("test.D")
    assert engine._resolver is not None
    _build_inheritance_edges([mod], graph, engine._resolver)


def test_enclosing_class_missing_parent_returns_none() -> None:
    mod = _make_module(
        "class S:\n"
        "    def run(self):\n"
        "        def inner():\n"
        "            pass\n"
        "        return inner\n",
        "test",
    )
    engine = CallGraphEngine(ModuleIndex([mod]))
    graph = engine.build([mod])
    graph.remove_node("test.S.run")
    extractor = EdgeExtractor(mod, graph, ImportResolver(engine.index))
    assert extractor._enclosing_class("test.S.run.<locals>.inner") is None


def test_direct_bases_missing_class_empty() -> None:
    mod = _make_module("def f():\n    pass\n", "test")
    engine = CallGraphEngine(ModuleIndex([mod]))
    graph = engine.build([mod])
    extractor = EdgeExtractor(mod, graph, ImportResolver(engine.index))
    assert extractor._direct_bases("nope.Missing") == []
