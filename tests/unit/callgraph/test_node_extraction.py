"""Tests for S3-T3 node extraction — functions, methods, lambdas, classes."""

import ast
from pathlib import Path

import networkx as nx

from pyreach.ast.builder import ASTBuilder, ModuleAST
from pyreach.ast.resolver import ModuleIndex
from pyreach.callgraph.engine import CallGraphEngine, EngineStats, NodeExtractor
from pyreach.callgraph.nodes import CGNode


def _parse_module(source: str, module_fqn: str = "test_mod") -> ModuleAST:
    """Parse source code into a ModuleAST for testing."""
    tree = ast.parse(source, filename="test_mod.py", mode="exec")
    return ModuleAST(
        file_path="test_mod.py",
        module_fqn=module_fqn,
        tree=tree,
    )


def _build_index(modules: list[ModuleAST]) -> ModuleIndex:
    return ModuleIndex(modules)


def _extract_nodes(module: ModuleAST, graph: nx.DiGraph) -> list[CGNode]:
    extractor = NodeExtractor(module, graph)
    return extractor.extract()


def test_function_node() -> None:
    source = """
def helper():
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 1
    assert nodes[0].fqn == "test_mod.helper"
    assert nodes[0].node_type == "FUNCTION"
    assert nodes[0].file_path == "test_mod.py"
    assert nodes[0].line_number == 2


def test_async_function_node() -> None:
    source = """
async def fetch():
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 1
    assert nodes[0].fqn == "test_mod.fetch"
    assert nodes[0].node_type == "FUNCTION"
    assert G.nodes["test_mod.fetch"]["is_async"] is True


def test_method_node() -> None:
    source = """
class Handler:
    def handle(self):
        pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 2
    class_node = next(n for n in nodes if n.node_type == "CLASS")
    method_node = next(n for n in nodes if n.node_type == "METHOD")
    assert class_node.fqn == "test_mod.Handler"
    assert method_node.fqn == "test_mod.Handler.handle"
    assert G.nodes["test_mod.Handler.handle"]["class_fqn"] == "test_mod.Handler"


def test_class_node() -> None:
    source = """
class Service:
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 1
    assert nodes[0].fqn == "test_mod.Service"
    assert nodes[0].node_type == "CLASS"


def test_lambda_node() -> None:
    source = """
f = lambda x: x + 1
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 1
    assert nodes[0].node_type == "LAMBDA"
    assert nodes[0].fqn.startswith("<lambda>:test_mod.py:")
    assert nodes[0].line_number == 2  # type: ignore[attr-defined]


def test_nested_lambda_node() -> None:
    source = """
f = lambda: (
    lambda: 1
)
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    lambdas = [n for n in nodes if n.node_type == "LAMBDA"]
    assert len(lambdas) == 2
    outer = next(n for n in lambdas if n.line_number == 2)
    inner = next(n for n in lambdas if n.line_number == 3)
    assert G.nodes[inner.fqn]["parent_fqn"] == outer.fqn


def test_nested_function_locals_fqn() -> None:
    source = """
def outer():
    def inner():
        pass
    return inner
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 2
    assert any(n.fqn == "test_mod.outer" for n in nodes)
    inner = next(n for n in nodes if "<locals>" in n.fqn)
    assert inner.fqn == "test_mod.outer.<locals>.inner"
    assert G.nodes["test_mod.outer.<locals>.inner"]["parent_fqn"] == "test_mod.outer"


def test_dedup_same_fqn() -> None:
    """Duplicate definitions (e.g. conditional) keep only the first."""
    source = """
def foo():
    pass

if False:
    def foo():
        pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    # Only one node for foo (the first one)
    foo_nodes = [n for n in nodes if n.fqn == "test_mod.foo"]
    assert len(foo_nodes) == 1


def test_static_method_modifier() -> None:
    source = """
class Service:
    @staticmethod
    def validate(x):
        pass

    @classmethod
    def from_config(cls, cfg):
        pass

    @property
    def name(self):
        return "test"
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    methods = [n for n in nodes if n.node_type == "METHOD"]
    assert len(methods) == 3

    modifiers = {m.fqn: G.nodes[m.fqn]["modifier"] for m in methods}
    assert modifiers["test_mod.Service.validate"] == "static"
    assert modifiers["test_mod.Service.from_config"] == "class"
    assert modifiers["test_mod.Service.name"] == "property"


def test_call_form_decorator_modifiers() -> None:
    source = """
class Service:
    @staticmethod()
    def validate(x):
        pass

    @pkg.cached()
    def compute(self):
        pass

    @mod.staticmethod()
    def check(self):
        pass

    @make().route
    def dynamic(self):
        pass

    @registry["key"]
    def handled(self):
        pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    modifiers = {n.fqn: G.nodes[n.fqn]["modifier"] for n in nodes if n.node_type == "METHOD"}
    assert modifiers["test_mod.Service.validate"] == "static"
    assert modifiers["test_mod.Service.check"] == "static"
    assert G.nodes["test_mod.Service.compute"]["decorators"] == ["pkg.cached"]
    assert G.nodes["test_mod.Service.dynamic"]["decorators"] == [""]
    assert G.nodes["test_mod.Service.handled"]["decorators"] == [""]


def test_line_and_file_metadata() -> None:
    source = """
# line 1
def my_func():  # line 3
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 1
    assert nodes[0].file_path == "test_mod.py"
    assert nodes[0].line_number == 3


def test_multiple_top_level_functions() -> None:
    source = """
def func_a():
    pass

def func_b():
    pass

class MyClass:
    def method_x(self):
        pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 4  # func_a, func_b, MyClass, MyClass.method_x
    fqns = {n.fqn for n in nodes}
    assert "test_mod.func_a" in fqns
    assert "test_mod.func_b" in fqns
    assert "test_mod.MyClass" in fqns
    assert "test_mod.MyClass.method_x" in fqns


def test_class_with_multiple_methods() -> None:
    source = """
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 3  # class + 2 methods
    fqns = {n.fqn for n in nodes}
    assert "test_mod.Calculator" in fqns
    assert "test_mod.Calculator.add" in fqns
    assert "test_mod.Calculator.subtract" in fqns


def test_no_functions_empty_module() -> None:
    source = """
x = 1
y = 2
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert len(nodes) == 0


def test_async_method() -> None:
    source = """
class API:
    async def get(self):
        pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    method = next(n for n in nodes if n.node_type == "METHOD")
    assert G.nodes[method.fqn]["is_async"] is True
    assert method.fqn == "test_mod.API.get"


def test_module_level_fqn_no_dot() -> None:
    """Single-file module with no package gets a simple FQN."""
    mod = _parse_module("def main(): pass", module_fqn="main_mod")
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    assert nodes[0].fqn == "main_mod.main"


def test_class_decorator_recorded() -> None:
    source = """
@dataclass
class Point:
    x: int
    y: int
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    cls = nodes[0]
    assert "dataclass" in G.nodes[cls.fqn]["decorators"]


def test_extracts_from_real_code_samples() -> None:
    """Extract nodes from S2-T7 real-world code samples.

    Verifies >=95% callable extraction from the corpus.
    """

    samples_dir = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "code_samples"
    builder = ASTBuilder(module_root=samples_dir)
    modules = []
    for path in sorted(samples_dir.rglob("*.py")):
        mod = builder.build_file(path)
        if mod is not None:
            modules.append(mod)

    assert modules, "No code samples found"

    engine = CallGraphEngine(ModuleIndex(modules))

    # Count actual callables in source
    total_callables = 0
    for mod in modules:
        for node in ast.walk(mod.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                total_callables += 1

    engine.build(modules)
    extracted = engine.stats.total

    # syntax_error.py is skipped by ASTBuilder (ParseError -> None), so the
    # denominator counts only parseable modules, matching the engine input.
    if total_callables > 0:
        ratio = extracted / total_callables
        assert ratio >= 0.95, f"Only {ratio * 100:.1f}% extracted ({extracted}/{total_callables})"


def test_callgraph_engine_build() -> None:
    """End-to-end: CallGraphEngine.build produces a DiGraph with nodes."""
    source = """
def main():
    pass

class Service:
    def run(self):
        pass
"""
    mod = _parse_module(source)
    engine = CallGraphEngine(_build_index([mod]))
    G = engine.build([mod])

    assert isinstance(G, nx.DiGraph)
    assert G.number_of_nodes() >= 3  # main, Service, Service.run

    stats = engine.stats
    assert stats.functions == 1
    assert stats.classes == 1
    assert stats.methods == 1
    assert stats.total == 3


def test_graph_nodes_have_correct_attributes() -> None:
    """Verify nodes in the graph have correct attributes attached."""
    source = """
def helper():
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    _extract_nodes(mod, G)

    assert "test_mod.helper" in G.nodes
    attrs = G.nodes["test_mod.helper"]
    assert attrs["node_type"] == "FUNCTION"
    assert attrs["file_path"] == "test_mod.py"
    assert attrs["line_number"] == 2
    assert attrs["is_async"] is False
    assert attrs["modifier"] == "none"
    assert attrs["class_fqn"] is None
    assert attrs["parent_fqn"] is None


def test_lambda_stats_tracked() -> None:
    """Lambda nodes are counted in stats."""
    source = "f = lambda x: x + 1"
    mod = _parse_module(source)
    engine = CallGraphEngine(ModuleIndex([mod]))
    engine.build([mod])
    stats = engine.stats
    assert stats.lambdas == 1
    assert stats.total == 1


def test_stats_property_returns_copy() -> None:
    """stats property returns the EngineStats dataclass."""
    mod = _parse_module("def f(): pass")
    engine = CallGraphEngine(ModuleIndex([mod]))
    engine.build([mod])
    stats = engine.stats
    assert isinstance(stats, EngineStats)
    assert stats.functions == 1
    assert stats.methods == 0
    assert stats.classes == 0
    assert stats.lambdas == 0
    assert stats.total == 1


def test_sentinel_nodes_added() -> None:
    """DYNAMIC and UNRESOLVED sentinel nodes are auto-added."""
    mod = _parse_module("def f(): pass")
    engine = CallGraphEngine(ModuleIndex([mod]))
    G = engine.build([mod])
    assert "<DYNAMIC>" in G.nodes
    assert "<UNRESOLVED>" in G.nodes
    assert G.nodes["<DYNAMIC>"]["is_sentinel"] is True
    assert G.nodes["<UNRESOLVED>"]["is_sentinel"] is True


def test_decorator_call_with_attribute() -> None:
    """@app.route() style decorators are detected."""
    source = """
class App:
    def route(self, path):
        pass

app = App()

@app.route("/")
def index():
    pass
"""
    mod = _parse_module(source)
    G = nx.DiGraph()
    nodes = _extract_nodes(mod, G)
    index_func = next(n for n in nodes if n.fqn == "test_mod.index")
    assert G.nodes[index_func.fqn]["decorators"] == ["app.route"]


def test_decorator_name_is_fallback() -> None:
    """Decorator that doesn't match returns False."""
    import ast

    deco = ast.Name(id="other")
    from pyreach.callgraph.engine import _decorator_name_is

    assert _decorator_name_is(deco, "staticmethod") is False
    assert _decorator_name_is(deco, "other") is True


def test_empty_module_has_sentinel_only() -> None:
    """Module with no callables still gets sentinel nodes."""
    mod = _parse_module("x = 1")
    engine = CallGraphEngine(ModuleIndex([mod]))
    G = engine.build([mod])
    assert G.number_of_nodes() == 2  # DYNAMIC + UNRESOLVED sentinels
    assert engine.stats.total == 0
