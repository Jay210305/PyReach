"""Call graph engine — node extraction pass (S3-T3) and edge extraction pass (S3-T4)."""

from __future__ import annotations

import ast
import builtins
import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import networkx as nx

from pyreach.ast.builder import ModuleAST
from pyreach.ast.resolver import ImportResolver, ModuleIndex
from pyreach.callgraph.edges import EdgeType, add_edge
from pyreach.callgraph.nodes import CGNode, NodeType, add_cgnode

logger = logging.getLogger(__name__)

Modifier = Literal["static", "class", "property", "none"]
SENTINEL_DYNAMIC = "<DYNAMIC>"
SENTINEL_UNRESOLVED = "<UNRESOLVED>"

CONF_STATIC = 1.0
CONF_DYNAMIC = 0.5
CONF_UNRESOLVED = 0.3


def _callable_fqn(module_fqn: str, name: str) -> str:
    return f"{module_fqn}.{name}" if module_fqn else name


def _nested_fqn(enclosing_fqn: str, name: str) -> str:
    return f"{enclosing_fqn}.<locals>.{name}"


def _lambda_fqn(file_path: str, lineno: int) -> str:
    return f"<lambda>:{file_path}:{lineno}"


def _is_static_method(decorator_list: list[ast.AST]) -> bool:
    return any(_decorator_name_is(dec, "staticmethod") for dec in decorator_list)


def _is_class_method(decorator_list: list[ast.AST]) -> bool:
    return any(_decorator_name_is(dec, "classmethod") for dec in decorator_list)


def _is_property(decorator_list: list[ast.AST]) -> bool:
    return any(_decorator_name_is(dec, "property") for dec in decorator_list)


def _decorator_name_is(decorator: ast.AST, name: str) -> bool:
    if isinstance(decorator, ast.Name) and decorator.id == name:
        return True
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == name:
            return True
        if isinstance(func, ast.Attribute) and func.attr == name:
            return True
    return False


def _resolve_decorator_modifier(decorator_list: list[ast.AST]) -> Modifier:
    if _is_static_method(decorator_list):
        return "static"
    if _is_class_method(decorator_list):
        return "class"
    if _is_property(decorator_list):
        return "property"
    return "none"


@dataclass
class _NodeMeta:
    """Scoping metadata attached to a graph node (consumed by the edge pass)."""

    file_path: str
    line_number: int | None
    class_fqn: str | None
    parent_fqn: str | None
    is_async: bool
    modifier: Modifier
    decorators: list[str]


class NodeExtractor(ast.NodeVisitor):
    """Extract CGNodes from a ModuleAST by walking definitions.

    FQN conventions (deterministic, deduplicated by FQN, first wins):
    - Module function ``foo`` in module ``m`` -> ``m.foo`` (FUNCTION).
    - Class ``C`` in module ``m`` -> ``m.C`` (CLASS).
    - Method ``meth`` of class ``m.C`` -> ``m.C.meth`` (METHOD, all decorators).
    - Nested function ``inner`` in ``m.outer`` -> ``m.outer.<locals>.inner``.
    - Lambda at ``rel_path:lineno`` -> ``<lambda>:rel_path:lineno`` (LAMBDA).
    - Duplicate FQNs (conditional defs, overloads) collapse to the first node.
    """

    def __init__(self, module: ModuleAST, graph: nx.DiGraph) -> None:
        self.module = module
        self.graph = graph
        self._seen_fqns: set[str] = set()
        self._extracted: list[CGNode] = []
        self._current_enclosing_fqn: str | None = None
        self._current_is_class: bool = False

    def extract(self) -> list[CGNode]:
        self._seen_fqns.clear()
        self._extracted.clear()
        self.visit(self.module.tree)
        return list(self._extracted)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node, node.name, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node, node.name, is_async=True)

    def _visit_callable(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        name: str,
        is_async: bool,
    ) -> None:
        modifier = _resolve_decorator_modifier(list(node.decorator_list))
        enclosing_fqn = self._current_enclosing_fqn

        if enclosing_fqn is None:
            fqn = _callable_fqn(self.module.module_fqn, name)
            node_type: NodeType = "FUNCTION"
            class_fqn: str | None = None
            parent_fqn: str | None = None
        elif self._current_is_class:
            fqn = _callable_fqn(enclosing_fqn, name)
            node_type = "METHOD"
            class_fqn = enclosing_fqn
            parent_fqn = enclosing_fqn
        else:
            fqn = _nested_fqn(enclosing_fqn, name)
            node_type = "FUNCTION"
            class_fqn = None
            parent_fqn = enclosing_fqn

        self._add_node(
            fqn,
            node_type,
            _NodeMeta(
                file_path=self.module.file_path,
                line_number=node.lineno,
                class_fqn=class_fqn,
                parent_fqn=parent_fqn,
                is_async=is_async,
                modifier=modifier,
                decorators=[self._decorator_fqn(d) for d in node.decorator_list],
            ),
        )

        old_enclosing = self._current_enclosing_fqn
        old_is_class = self._current_is_class
        self._current_enclosing_fqn = fqn
        self._current_is_class = False
        self.generic_visit(node)
        self._current_enclosing_fqn = old_enclosing
        self._current_is_class = old_is_class

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        fqn = _callable_fqn(self.module.module_fqn, node.name)

        self._add_node(
            fqn,
            "CLASS",
            _NodeMeta(
                file_path=self.module.file_path,
                line_number=node.lineno,
                class_fqn=None,
                parent_fqn=None,
                is_async=False,
                modifier="none",
                decorators=[self._decorator_fqn(d) for d in node.decorator_list],
            ),
        )

        old_enclosing = self._current_enclosing_fqn
        old_is_class = self._current_is_class
        self._current_enclosing_fqn = fqn
        self._current_is_class = True
        self.generic_visit(node)
        self._current_enclosing_fqn = old_enclosing
        self._current_is_class = old_is_class

    def visit_Lambda(self, node: ast.Lambda) -> None:
        fqn = _lambda_fqn(self.module.file_path, node.lineno)

        self._add_node(
            fqn,
            "LAMBDA",
            _NodeMeta(
                file_path=self.module.file_path,
                line_number=node.lineno,
                class_fqn=None,
                parent_fqn=self._current_enclosing_fqn,
                is_async=False,
                modifier="none",
                decorators=[],
            ),
        )

        old_enclosing = self._current_enclosing_fqn
        old_is_class = self._current_is_class
        self._current_enclosing_fqn = fqn
        self._current_is_class = False
        self.generic_visit(node)
        self._current_enclosing_fqn = old_enclosing
        self._current_is_class = old_is_class

    def _add_node(self, fqn: str, node_type: NodeType, meta: _NodeMeta) -> None:
        if fqn in self._seen_fqns:
            logger.debug("Duplicate FQN %s in %s, skipping", fqn, self.module.module_fqn)
            return
        self._seen_fqns.add(fqn)

        node = CGNode(
            fqn=fqn,
            file_path=meta.file_path,
            line_number=meta.line_number,
            node_type=node_type,
        )
        self._extracted.append(node)

        add_cgnode(self.graph, node)

        self.graph.nodes[fqn].update(
            {
                "class_fqn": meta.class_fqn,
                "parent_fqn": meta.parent_fqn,
                "is_async": meta.is_async,
                "modifier": meta.modifier,
                "decorators": meta.decorators,
            }
        )

    @staticmethod
    def _decorator_fqn(decorator: ast.AST) -> str:
        """Extract a string representation of a decorator for entry-point detection."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return ".".join(NodeExtractor._extract_attr_chain(func))
        if isinstance(decorator, ast.Attribute):
            return ".".join(NodeExtractor._extract_attr_chain(decorator))
        return ""

    @staticmethod
    def _extract_attr_chain(node: ast.AST) -> list[str]:
        """Extract attribute chain from an AST node (e.g., obj.method -> ['obj', 'method'])."""
        chain: list[str] = []
        current: ast.AST | None = node
        while current:
            if isinstance(current, ast.Attribute):
                chain.insert(0, current.attr)
                current = current.value
            elif isinstance(current, ast.Name):
                chain.insert(0, current.id)
                current = None
            else:
                return []
        return chain


_DYNAMIC_FUNCTION_NAMES = frozenset({"eval", "exec", "getattr", "setattr", "__import__", "apply"})


class EdgeExtractor(ast.NodeVisitor):
    """Resolve call targets and add ``caller -> callee`` edges (S3-T4).

    Caller attribution: the enclosing callable FQN tops a scope stack; calls in
    decorators and default values run at definition time, so they are visited
    with the outer scope. Calls directly in a class body are attributed to the
    class node; calls at module level are skipped (import-time code is not
    reachable from entry-point functions).
    """

    def __init__(self, module: ModuleAST, graph: nx.DiGraph, resolver: ImportResolver) -> None:
        self.module = module
        self.graph = graph
        self.resolver = resolver
        self._scope: list[tuple[str, bool]] = []
        self._instance_vars: dict[str, str] = {}
        self._saved_scopes: list[dict[str, str]] = []

    def extract(self) -> None:
        self._scope.clear()
        self._instance_vars.clear()
        self._saved_scopes.clear()
        self.visit(self.module.tree)

    @property
    def _caller(self) -> str | None:
        return self._scope[-1][0] if self._scope else None

    def _child_fqn(self, name: str) -> str:
        if not self._scope:
            return _callable_fqn(self.module.module_fqn, name)
        enclosing, is_class = self._scope[-1]
        if is_class:
            return _callable_fqn(enclosing, name)
        return _nested_fqn(enclosing, name)

    def visit_Import(self, node: ast.Import) -> None:
        if not self._scope:
            for alias in node.names:
                self._record_import(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if not self._scope and node.module is not None:
            self._record_import(node.module)

    def _record_import(self, module_fqn: str) -> None:
        add_edge(self.graph, self.module.module_fqn, module_fqn, "IMPORT", CONF_STATIC)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_callable(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_callable(node, node.name)

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> None:
        fqn = self._child_fqn(name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in list(node.args.defaults) + list(node.args.kw_defaults):
            if default is not None:
                self.visit(default)
        self._scope.append((fqn, False))
        self._saved_scopes.append(self._instance_vars)
        self._instance_vars = {}
        for stmt in node.body:
            self.visit(stmt)
        self._instance_vars = self._saved_scopes.pop()
        self._scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        fqn = _callable_fqn(self.module.module_fqn, node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword)
        self._scope.append((fqn, True))
        for stmt in node.body:
            self.visit(stmt)
        self._scope.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        fqn = _lambda_fqn(self.module.file_path, node.lineno)
        self._scope.append((fqn, False))
        self.generic_visit(node)
        self._scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._scope and not self._scope[-1][1]:
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                cls_fqn = self._resolve_class_name(value.func.id)
                if cls_fqn is not None:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self._instance_vars[target.id] = cls_fqn
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        caller = self._caller
        if caller is not None:
            self._resolve_call(caller, node)
        self.generic_visit(node)

    def _resolve_call(self, caller: str, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            self._resolve_name_call(caller, node, func.id)
        elif isinstance(func, ast.Attribute):
            self._resolve_attribute_call(caller, node, func)
        else:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)

    def _resolve_name_call(self, caller: str, node: ast.Call, name: str) -> None:
        if name in _DYNAMIC_FUNCTION_NAMES:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
            return
        resolved = self.resolver.resolve_name(name, self.module)
        if resolved is not None:
            if resolved in self.graph:
                self._record(caller, resolved, "STATIC", CONF_STATIC)
            elif resolved == name and hasattr(builtins, name):
                return
            else:
                self._record(caller, self._ensure_placeholder(resolved), "STATIC", CONF_STATIC)
            return
        local = _callable_fqn(self.module.module_fqn, name)
        if local in self.graph:
            self._record(caller, local, "STATIC", CONF_STATIC)
        else:
            self._fallback(caller, node)

    def _resolve_attribute_call(self, caller: str, node: ast.Call, func: ast.Attribute) -> None:
        inner = func.value
        if (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Name)
            and inner.func.id == "super"
        ):
            self._resolve_super_call(caller, node, func.attr)
            return
        chain = ImportResolver.extract_attribute_chain(func)
        if not chain:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
            return
        if chain[-1] == "import_module":
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
            return
        if chain[0] in ("self", "cls"):
            self._resolve_self_call(caller, node, chain)
            return
        if chain[0] in self._instance_vars:
            self._resolve_instance_call(caller, node, chain)
            return
        target = self.resolver.resolve_chain(chain, self.module)
        if target.resolved:
            callee = (
                target.fqn if target.fqn in self.graph else self._ensure_placeholder(target.fqn)
            )
            self._record(caller, callee, "STATIC", CONF_STATIC)
        elif chain[0] in self.module.symbol_table or chain[0] in self.module.imports:
            self._record(caller, self._ensure_placeholder(target.fqn), "STATIC", CONF_STATIC)
        else:
            self._fallback(caller, node)

    def _resolve_self_call(self, caller: str, node: ast.Call, chain: list[str]) -> None:
        if len(chain) != 2:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
            return
        class_fqn = self._enclosing_class(caller)
        if class_fqn is None:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", CONF_UNRESOLVED)
            return
        self._resolve_method_call(caller, node, class_fqn, chain[1])

    def _resolve_instance_call(self, caller: str, node: ast.Call, chain: list[str]) -> None:
        if len(chain) != 2:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
            return
        self._resolve_method_call(caller, node, self._instance_vars[chain[0]], chain[1])

    def _resolve_method_call(
        self, caller: str, node: ast.Call, class_fqn: str, method: str
    ) -> None:
        found = self._lookup_in_hierarchy(class_fqn, method)
        if found is not None:
            self._record(caller, found, "STATIC", CONF_STATIC)
        else:
            self._fallback(caller, node)

    def _resolve_super_call(self, caller: str, node: ast.Call, method: str) -> None:
        class_fqn = self._enclosing_class(caller)
        bases = self._direct_bases(class_fqn) if class_fqn is not None else []
        for base in bases:
            found = self._lookup_in_hierarchy(base, method)
            if found is not None:
                self._record(caller, found, "STATIC", CONF_STATIC)
                return
        self._fallback(caller, node)

    def _fallback(self, caller: str, node: ast.Call) -> None:
        if self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", CONF_DYNAMIC)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", CONF_UNRESOLVED)

    def _resolve_class_name(self, name: str) -> str | None:
        resolved = self.resolver.resolve_name(name, self.module)
        if (
            resolved is not None
            and resolved in self.graph
            and self.graph.nodes[resolved].get("node_type") == "CLASS"
        ):
            return resolved
        local = _callable_fqn(self.module.module_fqn, name)
        if local in self.graph and self.graph.nodes[local].get("node_type") == "CLASS":
            return local
        return None

    def _enclosing_class(self, caller: str) -> str | None:
        seen: set[str] = set()
        current: str | None = caller
        while current is not None and current not in seen:
            seen.add(current)
            if current not in self.graph:
                return None
            attrs = self.graph.nodes[current]
            class_fqn = attrs.get("class_fqn")
            if isinstance(class_fqn, str):
                return class_fqn
            parent = attrs.get("parent_fqn")
            current = parent if isinstance(parent, str) else None
        return None

    def _direct_bases(self, class_fqn: str) -> list[str]:
        if class_fqn not in self.graph:
            return []
        return sorted(
            succ
            for succ in self.graph.successors(class_fqn)
            if succ != class_fqn
            and self.graph.get_edge_data(class_fqn, succ).get("edge_type") == "INHERITANCE"
        )

    def _lookup_in_hierarchy(self, class_fqn: str, method: str) -> str | None:
        candidate = f"{class_fqn}.{method}"
        if candidate in self.graph:
            return candidate
        visited: set[str] = {class_fqn}
        queue: deque[str] = deque([class_fqn])
        while queue:
            current = queue.popleft()
            for base in self._direct_bases(current):
                if base in visited:
                    continue
                visited.add(base)
                candidate = f"{base}.{method}"
                if candidate in self.graph:
                    return candidate
                queue.append(base)
        return None

    def _ensure_placeholder(self, fqn: str) -> str:
        if fqn not in self.graph:
            placeholder = CGNode(fqn=fqn, file_path=None, line_number=None, node_type="FUNCTION")
            add_cgnode(self.graph, placeholder)
            self.graph.nodes[fqn].update(
                {
                    "is_placeholder": True,
                    "class_fqn": None,
                    "parent_fqn": None,
                    "is_async": False,
                    "modifier": "none",
                    "decorators": [],
                }
            )
        return fqn

    def _record(self, caller: str, callee: str, edge_type: EdgeType, confidence: float) -> None:
        add_edge(self.graph, caller, callee, edge_type, confidence)

    @staticmethod
    def _has_star_args(node: ast.Call) -> bool:
        return any(isinstance(arg, ast.Starred) for arg in node.args) or any(
            kw.arg is None for kw in node.keywords
        )


def _resolve_base_fqn(
    base: ast.AST, module: ModuleAST, resolver: ImportResolver, graph: nx.DiGraph
) -> str | None:
    if isinstance(base, ast.Name):
        resolved = resolver.resolve_name(base.id, module)
        if resolved is not None and resolved in graph:
            return resolved
        local = _callable_fqn(module.module_fqn, base.id)
        return local if local in graph else None
    if isinstance(base, ast.Attribute):
        chain = ImportResolver.extract_attribute_chain(base)
        if chain:
            target = resolver.resolve_chain(chain, module)
            if target.resolved and target.fqn in graph:
                return target.fqn
    return None


def _build_inheritance_edges(
    modules: Iterable[ModuleAST], graph: nx.DiGraph, resolver: ImportResolver
) -> None:
    for module in modules:
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            sub = _callable_fqn(module.module_fqn, node.name)
            if sub not in graph:
                continue
            for base in node.bases:
                base_fqn = _resolve_base_fqn(base, module, resolver, graph)
                if base_fqn is not None and base_fqn != sub:
                    add_edge(graph, sub, base_fqn, "INHERITANCE", CONF_STATIC)


@dataclass
class EngineStats:
    """Node counts by type from the last build."""

    functions: int = 0
    methods: int = 0
    classes: int = 0
    lambdas: int = 0
    total: int = 0


class CallGraphEngine:
    """Builds a NetworkX DiGraph call graph from ModuleASTs.

    Three-pass construction:
    1. Node pass (S3-T3): extract all callable/class nodes
    2. Inheritance pass (S3-T4): link subclasses to resolved base classes
    3. Edge pass (S3-T4): resolve call targets and add edges
    """

    def __init__(self, index: ModuleIndex) -> None:
        self.index = index
        self._resolver: ImportResolver | None = None
        self._stats = EngineStats()

    def build(self, modules: Iterable[ModuleAST]) -> nx.DiGraph:
        """Build the call graph from parsed modules.

        Modules must carry S2 symbol tables for cross-module resolution;
        same-module calls additionally fall back to local node lookup.
        """
        graph = nx.DiGraph()
        self._stats = EngineStats()
        self._resolver = ImportResolver(self.index)
        ordered = sorted(modules, key=lambda mod: mod.module_fqn)

        for sentinel in (SENTINEL_DYNAMIC, SENTINEL_UNRESOLVED):
            if sentinel not in graph:
                graph.add_node(sentinel, is_sentinel=True)

        for module in ordered:
            extractor = NodeExtractor(module, graph)
            for node in extractor.extract():
                self._update_stats(node.node_type)

        _build_inheritance_edges(ordered, graph, self._resolver)

        for module in ordered:
            EdgeExtractor(module, graph, self._resolver).extract()

        return graph

    def _update_stats(self, node_type: NodeType) -> None:
        self._stats.total += 1
        match node_type:
            case "FUNCTION":
                self._stats.functions += 1
            case "METHOD":
                self._stats.methods += 1
            case "CLASS":
                self._stats.classes += 1
            case "LAMBDA":
                self._stats.lambdas += 1

    @property
    def stats(self) -> EngineStats:
        """Return node counts by type from the last build."""
        return self._stats
