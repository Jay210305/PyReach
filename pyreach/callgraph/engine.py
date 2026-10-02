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

# mypy: disable-error-code="import-untyped"
from pyreach.ast.builder import ModuleAST
from pyreach.ast.resolver import ImportResolver, ModuleIndex
from pyreach.callgraph.edges import CGEdge, EdgeType
from pyreach.callgraph.nodes import CGNode, NodeType, add_cgnode

logger = logging.getLogger(__name__)

Modifier = Literal["static", "class", "property", "none"]
SENTINEL_DYNAMIC = "<DYNAMIC>"
SENTINEL_UNRESOLVED = "<UNRESOLVED>"


def _callable_fqn(module_fqn: str, name: str) -> str:
    return f"{module_fqn}.{name}" if module_fqn else name


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


class NodeExtractor(ast.NodeVisitor):
    """Extract CGNodes from a ModuleAST by walking top-level definitions.

    FQN conventions (deterministic, deduplicated by FQN, first wins):
    - Module function ``foo`` in module ``m`` -> ``m.foo`` (FUNCTION).
    - Class ``C`` in module ``m`` -> ``m.C`` (CLASS).
    - Method ``meth`` of class ``m.C`` -> ``m.C.meth`` (METHOD, all decorators).
    - Nested function ``inner`` in ``m.outer`` -> ``m.outer.<locals>.inner``.
    - Lambda at ``rel_path:lineno`` -> ``<lambda>:rel_path:lineno`` (LAMBDA).
    - Duplicate FQNs (conditional defs, overloads) collapse to the first node.

    Handles:
    - Module-level FunctionDef/AsyncFunctionDef -> FUNCTION nodes
    - ClassDef -> CLASS nodes
    - Methods (FunctionDef inside ClassDef) -> METHOD nodes
    - Lambda -> LAMBDA nodes with ``<lambda>:file:line`` FQN
    - Nested functions -> ``enclosing.<locals>.name`` FQN
    - Static/classmethod/property decorators -> modifier attribute
    - Inheritance bases -> recorded as class metadata for S3-T4
    - Decorators -> recorded for S3-T7 entry-point detection
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
        # Determine enclosing context from the visitor stack
        # ast.NodeVisitor doesn't track parent, so we use a simple approach:
        # check if we're inside a ClassDef by looking at the path we've built
        enclosing_fqn = self._current_enclosing_fqn
        if enclosing_fqn is None:
            # Module-level function (module FQN comes from S2-T4, never recomputed here)
            fqn = _callable_fqn(self.module.module_fqn, name)
            node_type: NodeType = "FUNCTION"
            class_fqn: str | None = None
            parent_fqn: str | None = None
        else:
            # Method inside a class
            fqn = f"{enclosing_fqn}.{name}"
            node_type = "METHOD"
            class_fqn = enclosing_fqn
            parent_fqn = enclosing_fqn

        # Handle nested functions (enclosing is a function, not a class)
        if enclosing_fqn is not None and not self._current_is_class:
            # Nested function inside another function
            fqn = f"{enclosing_fqn}.<locals>.{name}"
            parent_fqn = enclosing_fqn
            class_fqn = None

        self._add_node(
            fqn=fqn,
            node_type=node_type,
            file_path=self.module.file_path,
            line_number=node.lineno,
            class_fqn=class_fqn,
            parent_fqn=parent_fqn,
            is_async=is_async,
            modifier=modifier,
            decorators=[self._decorator_fqn(d) for d in node.decorator_list],
        )

        # Recurse into body but don't track enclosing for nested functions
        # We need to track enclosing for nested functions
        old_enclosing = self._current_enclosing_fqn
        old_is_class = self._current_is_class
        self._current_enclosing_fqn = fqn
        self._current_is_class = False
        self.generic_visit(node)
        self._current_enclosing_fqn = old_enclosing
        self._current_is_class = old_is_class

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        fqn = _callable_fqn(self.module.module_fqn, node.name)

        # Resolve bases via symbol table
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(".".join(self._extract_attr_chain(base)))
            else:
                bases.append("")

        decorators = [self._decorator_fqn(d) for d in node.decorator_list]

        self._add_node(
            fqn=fqn,
            node_type="CLASS",
            file_path=self.module.file_path,
            line_number=node.lineno,
            class_fqn=None,
            parent_fqn=None,
            is_async=False,
            modifier="none",
            decorators=decorators,
            bases=bases,
        )

        old_enclosing = self._current_enclosing_fqn
        old_is_class = self._current_is_class
        self._current_enclosing_fqn = fqn
        self._current_is_class = True
        self.generic_visit(node)
        self._current_enclosing_fqn = old_enclosing
        self._current_is_class = old_is_class

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # Lambda FQN: <lambda>:rel_path:lineno
        rel_path = self.module.file_path
        fqn = f"<lambda>:{rel_path}:{node.lineno}"

        self._add_node(
            fqn=fqn,
            node_type="LAMBDA",
            file_path=self.module.file_path,
            line_number=node.lineno,
            class_fqn=None,
            parent_fqn=self._current_enclosing_fqn,
            is_async=False,
            modifier="none",
            decorators=[],
        )
        # Don't recurse into lambda body for nested definitions
        # (lambdas can't contain nested defs anyway)

    def _add_node(
        self,
        fqn: str,
        node_type: NodeType,
        file_path: str,
        line_number: int | None,
        class_fqn: str | None,
        parent_fqn: str | None,
        is_async: bool,
        modifier: Modifier,
        decorators: list[str],
        bases: list[str] | None = None,
    ) -> None:
        if fqn in self._seen_fqns:
            logger.debug("Duplicate FQN %s in %s, skipping", fqn, self.module.module_fqn)
            return
        self._seen_fqns.add(fqn)

        node = CGNode(
            fqn=fqn,
            file_path=file_path,
            line_number=line_number,
            node_type=node_type,
        )
        self._extracted.append(node)

        add_cgnode(self.graph, node)

        # Attach scoping metadata consumed by S3-T4
        attrs: dict[str, object] = {
            "node_type": node_type,
            "file_path": file_path,
            "line_number": line_number,
            "class_fqn": class_fqn,
            "parent_fqn": parent_fqn,
            "is_async": is_async,
            "modifier": modifier,
            "decorators": decorators,
            "bases": bases or [],
        }
        self.graph.nodes[fqn].update(attrs)

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

    # NOTE: enclosing-context state lives on the instance (see __init__),
    # never on the class, so parallel NodeExtractor instances cannot leak scope.


_DYNAMIC_FUNCTION_NAMES = frozenset({"eval", "exec", "getattr", "setattr", "__import__", "apply"})

_EDGE_TYPE_PRECEDENCE = {"STATIC": 3, "INHERITANCE": 2, "DYNAMIC": 1}


def _add_graph_edge(
    graph: nx.DiGraph, caller: str, callee: str, edge_type: EdgeType, confidence: float
) -> None:
    """Add an edge, keeping the winner on duplicates.

    Precedence: higher confidence wins; on confidence ties the stronger type
    wins (``STATIC`` > ``INHERITANCE`` > ``DYNAMIC``). ``DiGraph`` collapses
    parallel edges with last-write-wins, so this guard is what keeps edge
    insertion order-independent and deterministic.
    """
    existing = graph.get_edge_data(caller, callee)
    if existing is not None:
        old_key = (
            float(existing.get("confidence", 0.0)),
            _EDGE_TYPE_PRECEDENCE.get(str(existing.get("edge_type", "DYNAMIC")), 0),
        )
        if (confidence, _EDGE_TYPE_PRECEDENCE[edge_type]) <= old_key:
            return
    graph.add_edge(caller, callee, edge_type=edge_type, confidence=confidence)


class EdgeExtractor(ast.NodeVisitor):
    """Resolve call targets and add ``caller -> callee`` edges (S3-T4).

    Caller attribution: the enclosing callable FQN tops a scope stack; calls in
    decorators and default values run at definition time, so they are visited
    with the outer scope. Calls directly in a class body are attributed to the
    class node; calls at module level are skipped (import-time code is not
    reachable from entry-point functions).

    Target resolution order per call site: dynamic patterns (``eval``,
    ``import_module``, ...) -> ``super()`` -> ``self``/``cls`` -> tracked
    ``x = Class()`` instances -> ``ImportResolver`` -> same-module fallback ->
    ``<DYNAMIC>``/``<UNRESOLVED>`` sentinels. Anything the resolver points at
    outside the parsed corpus becomes a placeholder node so library calls stay
    visible to reachability; bare builtins (``len``, ``print``) produce no edge
    since they can never be vulnerable symbols.
    """

    def __init__(self, module: ModuleAST, graph: nx.DiGraph, resolver: ImportResolver) -> None:
        self.module = module
        self.graph = graph
        self.resolver = resolver
        self._scope: list[tuple[str, bool]] = []
        self._instance_vars: dict[str, str] = {}
        self._saved_scopes: list[dict[str, str]] = []
        self._edges: list[CGEdge] = []

    def extract(self) -> list[CGEdge]:
        self._scope.clear()
        self._instance_vars.clear()
        self._saved_scopes.clear()
        self._edges.clear()
        self.visit(self.module.tree)
        return list(self._edges)

    @property
    def _caller(self) -> str | None:
        return self._scope[-1][0] if self._scope else None

    def _child_fqn(self, name: str) -> str:
        if not self._scope:
            return _callable_fqn(self.module.module_fqn, name)
        enclosing, is_class = self._scope[-1]
        if is_class:
            return f"{enclosing}.{name}"
        return f"{enclosing}.<locals>.{name}"

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
        fqn = f"<lambda>:{self.module.file_path}:{node.lineno}"
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
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)

    def _resolve_name_call(self, caller: str, node: ast.Call, name: str) -> None:
        if name in _DYNAMIC_FUNCTION_NAMES:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
            return
        resolved = self.resolver.resolve_name(name, self.module)
        if resolved is not None:
            if resolved in self.graph:
                self._record(caller, resolved, "STATIC", 1.0)
            elif resolved == name and hasattr(builtins, name):
                return
            else:
                self._record(caller, self._ensure_placeholder(resolved), "STATIC", 1.0)
            return
        local = _callable_fqn(self.module.module_fqn, name)
        if local in self.graph:
            self._record(caller, local, "STATIC", 1.0)
        elif self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)

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
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
            return
        if chain[-1] == "import_module":
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
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
            self._record(caller, callee, "STATIC", 1.0)
        elif chain[0] in self.module.symbol_table or chain[0] in self.module.imports:
            self._record(caller, self._ensure_placeholder(target.fqn), "STATIC", 1.0)
        elif self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)

    def _resolve_self_call(self, caller: str, node: ast.Call, chain: list[str]) -> None:
        if len(chain) != 2:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
            return
        class_fqn = self._enclosing_class(caller)
        if class_fqn is None:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)
            return
        found = self._lookup_in_hierarchy(class_fqn, chain[1])
        if found is not None:
            self._record(caller, found, "STATIC", 1.0)
        elif self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)

    def _resolve_instance_call(self, caller: str, node: ast.Call, chain: list[str]) -> None:
        if len(chain) != 2:
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
            return
        found = self._lookup_in_hierarchy(self._instance_vars[chain[0]], chain[1])
        if found is not None:
            self._record(caller, found, "STATIC", 1.0)
        elif self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)

    def _resolve_super_call(self, caller: str, node: ast.Call, method: str) -> None:
        class_fqn = self._enclosing_class(caller)
        bases = self._direct_bases(class_fqn) if class_fqn is not None else []
        for base in bases:
            found = self._lookup_in_hierarchy(base, method)
            if found is not None:
                self._record(caller, found, "STATIC", 1.0)
                return
        if self._has_star_args(node):
            self._record(caller, SENTINEL_DYNAMIC, "DYNAMIC", 0.5)
        else:
            self._record(caller, SENTINEL_UNRESOLVED, "DYNAMIC", 0.3)

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
                    "bases": [],
                }
            )
        return fqn

    def _record(self, caller: str, callee: str, edge_type: EdgeType, confidence: float) -> None:
        self._add_edge(caller, callee, edge_type, confidence)
        caller_node = self.graph.nodes[caller].get("node") or CGNode(fqn=caller)
        callee_node = self.graph.nodes[callee].get("node") or CGNode(fqn=callee)
        self._edges.append(
            CGEdge(
                caller=caller_node,
                callee=callee_node,
                edge_type=edge_type,
                confidence=confidence,
            )
        )

    def _add_edge(self, caller: str, callee: str, edge_type: EdgeType, confidence: float) -> None:
        _add_graph_edge(self.graph, caller, callee, edge_type, confidence)

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
                    _add_graph_edge(graph, sub, base_fqn, "INHERITANCE", 1.0)


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

        Args:
            modules: Iterable of ModuleAST objects from the AST pipeline.

        Returns:
            A NetworkX DiGraph with nodes and edges.
        """
        graph = nx.DiGraph()
        self._stats = EngineStats()
        self._resolver = ImportResolver(self.index)
        ordered = sorted(modules, key=lambda mod: mod.module_fqn)

        # Add sentinel nodes for dynamic/unresolved calls
        for sentinel in (SENTINEL_DYNAMIC, SENTINEL_UNRESOLVED):
            if sentinel not in graph:
                graph.add_node(sentinel, node_type="SENTINEL", is_sentinel=True)

        # Node pass: extract all callable nodes
        for module in ordered:
            extractor = NodeExtractor(module, graph)
            nodes = extractor.extract()
            for node in nodes:
                self._update_stats(node.node_type)

        # Inheritance pass must precede call resolution (self/super lookups
        # follow INHERITANCE edges up the hierarchy).
        _build_inheritance_edges(ordered, graph, self._resolver)

        # Edge pass: resolve call targets and add edges
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
