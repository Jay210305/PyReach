# AST and Call Graph Engine

## 1. Abstract Syntax Tree (AST) Pipeline

### 1.1 Parsing Strategy

PyReach uses the CPython standard library `ast` module (introduced in Python 3.9, stable in 3.10+) to parse source code without execution. This is a purely syntactic analysis — no bytecode compilation or runtime instrumentation.

```python
import ast

def parse_source(file_path: str, source_text: str) -> ast.AST:
    try:
        tree = ast.parse(source_text, filename=file_path, mode='exec')
    except SyntaxError as exc:
        raise ParseError(f"Syntax error in {file_path}:{exc.lineno}: {exc.msg}") from exc
    return tree
```

### 1.2 Module Fully Qualified Name (FQN) Computation

Given a file path relative to the project root or site-packages root, compute the module FQN:

```
src/myapp/utils/http.py  ->  myapp.utils.http
site-packages/requests/api.py  ->  requests.api
site-packages/requests/__init__.py  ->  requests
```

Algorithm:
1. Identify package root (directory containing `__init__.py` or top-level module).
2. Strip `.py` extension.
3. Replace path separators with dots.
4. For `__init__.py`, use the package name only.

### 1.3 Symbol Table Construction

Each `ModuleAST` contains a symbol table mapping local identifiers to their fully qualified origins.

**Import Types Handled:**

| Import Syntax | Symbol Table Entry | Example |
|---------------|-------------------|---------|
| `import os` | `os` -> `os` | |
| `import numpy as np` | `np` -> `numpy` | |
| `from collections import OrderedDict` | `OrderedDict` -> `collections.OrderedDict` | |
| `from collections import OrderedDict as OD` | `OD` -> `collections.OrderedDict` | |
| `from . import sibling` | `sibling` -> `current_pkg.sibling` | |
| `from ..parent import mod` | `mod` -> `parent.mod` | |
| `from module import *` | All public names from `module` | Heuristic: parse `module`'s `__all__` if present |

**AST Nodes Traversed:**
- `ast.Import`
- `ast.ImportFrom`

**Star Import Resolution:**
1. Locate the target module's source file.
2. Parse its AST.
3. If `__all__` is defined as a list of strings, use those names.
4. Otherwise, use all top-level function/class/variable definitions.

### 1.4 AST Node Types of Interest

For call graph construction, the following AST node types are relevant:

| Node Type | Relevance |
|-----------|-----------|
| `ast.FunctionDef` / `ast.AsyncFunctionDef` | Function/method definitions (graph nodes) |
| `ast.ClassDef` | Class definitions (container for methods, inheritance edges) |
| `ast.Call` | Call sites (graph edges) |
| `ast.Lambda` | Anonymous functions (graph nodes, limited scope) |
| `ast.Name` / `ast.Attribute` | Identifiers in call expressions |
| `ast.Assign` | Variable assignments (for simple binding tracking) |

## 2. Call Graph Engine

### 2.1 Node Types

```python
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass(frozen=True)
class CGNode:
    fqn: str
    file_path: Optional[str]
    line_number: Optional[int]
    node_type: Literal["FUNCTION", "METHOD", "CLASS", "LAMBDA"]
```

**FQN Examples:**
- `myapp.main` (module-level function)
- `myapp.handlers.UserController.get` (class method)
- `requests.api.get` (library function)
- `<lambda>:myapp.utils:42` (lambda at file:line)

### 2.2 Edge Types

| Edge Type | Description | Confidence |
|-----------|-------------|------------|
| `STATIC` | Direct, resolvable function call | 1.0 |
| `DYNAMIC` | Call through `eval`, `exec`, `getattr`, `apply`, `functools.partial`, dynamic `import` | 0.5 |
| `INHERITANCE` | Method override / super call | 1.0 |
| `IMPORT` | Module-level import leading to usage | 1.0 |

### 2.3 Graph Construction Algorithm

```
Input: List[ModuleAST]
Output: networkx.DiGraph

1. Initialize empty DiGraph G.

2. NODE CREATION PASS:
   For each ModuleAST m:
     For each ast.FunctionDef / ast.AsyncFunctionDef func in m.tree.body:
       fqn = compute_fqn(m.module_fqn, func.name)
       G.add_node(CGNode(fqn=fqn, file_path=m.file_path, line_number=func.lineno, node_type="FUNCTION"))
     For each ast.ClassDef cls in m.tree.body:
       For each method in cls.body (if FunctionDef):
         fqn = compute_fqn(m.module_fqn, cls.name, method.name)
         G.add_node(CGNode(fqn=fqn, ...))
       Add INHERITANCE edges to parent classes if resolvable.

3. EDGE CREATION PASS:
   For each ModuleAST m:
     For each function node f in m:
       For each ast.Call call in f's body (walk AST subtree):
         callee_fqn = resolve_call_target(call, m.symbol_table, f)
         If callee_fqn is resolved:
           G.add_edge(f.fqn, callee_fqn, edge_type="STATIC", confidence=1.0)
         Else if call contains dynamic patterns:
           G.add_edge(f.fqn, "<DYNAMIC>", edge_type="DYNAMIC", confidence=0.5)
         Else:
           G.add_edge(f.fqn, "<UNRESOLVED>", edge_type="DYNAMIC", confidence=0.3)

4. Return G.
```

### 2.4 Call Target Resolution

Given an `ast.Call` node, resolve the callee's fully qualified name:

```python
def resolve_call_target(call: ast.Call, symbol_table: dict, caller_fqn: str) -> Optional[str]:
    func = call.func
    if isinstance(func, ast.Name):
        # Direct call: foo()
        local_name = func.id
        return symbol_table.get(local_name, local_name)
    elif isinstance(func, ast.Attribute):
        # Attribute chain: obj.method() or pkg.subpkg.func()
        chain = extract_attribute_chain(func)
        # chain = ["requests", "get"]
        if chain[0] in symbol_table:
            base = symbol_table[chain[0]]
            return ".".join([base] + chain[1:])
        else:
            # Maybe a class method call: self.method()
            if chain[0] == "self":
                return resolve_self_method(caller_fqn, chain[1])
            return ".".join(chain)
    return None
```

**`extract_attribute_chain`** recursively unpacks `ast.Attribute` nodes:
```python
def extract_attribute_chain(node: ast.AST) -> List[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    elif isinstance(node, ast.Attribute):
        return extract_attribute_chain(node.value) + [node.attr]
    return []
```

### 2.5 Method Resolution

**Instance Methods (`self`)**:  
Given a caller `myapp.handlers.UserController.get` and a call `self.authenticate()`, the callee is resolved to `myapp.handlers.UserController.authenticate` by replacing the last component of the caller's FQN.

**Class Methods (`cls`)**:  
Similar to `self`, but on the class node itself.

**Inheritance**:  
If `self.method()` is not found in the current class, traverse `INHERITANCE` edges to parent classes and check there. This requires building an inheritance graph alongside the call graph.

### 2.6 Dynamic Pattern Detection

The following patterns trigger a `DYNAMIC` edge (conservative over-approximation):

| Pattern | AST Signature | Action |
|---------|---------------|--------|
| `eval(expr)` | `ast.Call(func=ast.Name(id='eval'))` | DYNAMIC edge |
| `exec(code)` | `ast.Call(func=ast.Name(id='exec'))` | DYNAMIC edge |
| `getattr(obj, name)` | `ast.Call(func=ast.Name(id='getattr'))` | DYNAMIC edge |
| `setattr(obj, name, val)` | `ast.Call(func=ast.Name(id='setattr'))` | DYNAMIC edge |
| `apply(func, args)` | `ast.Call(func=ast.Name(id='apply'))` | DYNAMIC edge |
| `importlib.import_module(name)` | `ast.Call(func=ast.Attribute(...import_module))` | DYNAMIC edge |
| `__import__(name)` | `ast.Call(func=ast.Name(id='__import__'))` | DYNAMIC edge |
| `func(*args, **kwargs)` where func is unresolved | `ast.Call(func=ast.Name)` not in symbol table | DYNAMIC edge with confidence 0.3 |
| Decorators with dynamic behavior | `ast.Call` inside `ast.decorator_list` | Flag caller as potentially dynamic |

## 3. Reachability Analyzer

### 3.1 Entry Point Detection

Entry points are the roots from which reachability is computed.

**Auto-Detection:**
1. Any top-level function named `main`.
2. Any code block under `if __name__ == "__main__":`.
3. Any function decorated with known framework decorators:
   - FastAPI: `@app.get`, `@app.post`, etc.
   - Flask: `@app.route`
   - Django: Not auto-detected (too diverse); rely on CLI `-e` flag.

**CLI Override:**
Users can explicitly declare entry points via `-e package.module:function` or `.pyreach.yml`.

### 3.2 Bounded Traversal Algorithm

```python
from collections import deque
import networkx as nx

def analyze_reachability(
    graph: nx.DiGraph,
    entry_points: List[str],
    vulnerable_symbols: List[str],
    max_depth: int = 5
) -> Dict[str, ReachabilityResult]:
    results = {}
    memo = {}  # node_fqn -> {symbol: status}

    for symbol in vulnerable_symbols:
        status = "NOT_REACHABLE"
        paths = []

        for entry in entry_points:
            if entry not in graph:
                continue
            
            # BFS with depth tracking
            queue = deque([(entry, [entry], 0)])
            visited = set()

            while queue:
                current, path, depth = queue.popleft()
                
                if depth > max_depth:
                    continue
                if current in visited:
                    continue
                visited.add(current)

                # Check if current node is the vulnerable symbol
                if current == symbol:
                    status = "REACHABLE"
                    paths.append(path + [symbol])
                    break  # Found reachable path from this entry

                # Check edge types for dynamic patterns
                for successor in graph.successors(current):
                    edge_data = graph.get_edge_data(current, successor)
                    edge_type = edge_data.get("edge_type", "STATIC")
                    
                    if edge_type == "DYNAMIC":
                        # Conservative: if dynamic edge is on any path to symbol, mark potentially
                        if _can_reach_via_dynamic(graph, successor, symbol, max_depth - depth):
                            status = "POTENTIALLY_REACHABLE"
                    
                    queue.append((successor, path + [successor], depth + 1))

            if status == "REACHABLE":
                break

        results[symbol] = ReachabilityResult(
            symbol=symbol,
            status=status,
            paths=paths,
            entry_points=[entry for entry in entry_points if _has_path(graph, entry, symbol, max_depth)]
        )

    return results
```

### 3.3 Memoization Strategy

To avoid recomputing reachability for shared subgraphs across multiple vulnerabilities:

```python
# Per-run cache in memory
_reachability_cache: Dict[Tuple[str, str, int], str] = {}

def cached_is_reachable(graph, entry, symbol, max_depth) -> str:
    key = (entry, symbol, max_depth)
    if key not in _reachability_cache:
        _reachability_cache[key] = _compute_reachability(graph, entry, symbol, max_depth)
    return _reachability_cache[key]
```

### 3.4 Cycle Handling

Python allows recursive calls. The BFS `visited` set prevents infinite loops. For mutually recursive functions, the algorithm correctly explores up to `max_depth` hops.

## 4. Heuristic Design for Conservative Analysis

### 4.1 Over-Approximation Rule

**Principle**: When uncertain, classify as `POTENTIALLY_REACHABLE`. This ensures **zero critical false negatives** — we never incorrectly dismiss an exploitable vulnerability.

### 4.2 Decision Matrix

| Condition | Classification |
|-----------|---------------|
| Static path exists from entry point to vulnerable symbol (length <= k) | **REACHABLE** |
| No static path exists; no dynamic edges in subgraph | **NOT_REACHABLE** |
| No static path exists; dynamic edge present in any path to symbol | **POTENTIALLY_REACHABLE** |
| Symbol is in a package not imported by application | **NOT_REACHABLE** |
| Symbol is in an imported package but call chain unresolved | **POTENTIALLY_REACHABLE** |
| `eval` / `exec` present in call chain | **POTENTIALLY_REACHABLE** |
| `getattr` with variable attribute name | **POTENTIALLY_REACHABLE** |

### 4.3 Example Scenario

```python
# myapp/main.py
from myapp.client import ApiClient

def main():
    client = ApiClient()
    client.fetch_data()  # -> myapp.client.ApiClient.fetch_data

# myapp/client.py
import requests

class ApiClient:
    def fetch_data(self):
        requests.get("https://api.example.com")  # -> requests.api.get
```

**Vulnerability**: `requests.api.get` has CVE-2023-XXXX.  
**Call Graph Path**: `main` -> `ApiClient.fetch_data` -> `requests.api.get`  
**Result**: **REACHABLE** (all static edges, depth 2).

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
