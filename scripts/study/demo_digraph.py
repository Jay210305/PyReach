"""Demo for S3-T1 — DiGraph fundamentals, serialization, bounded BFS on cycle."""
import json
import time
from collections import deque

import networkx as nx
from networkx.readwrite import json_graph


def bounded_reachable(G: nx.DiGraph, entry: str, target: str, max_depth: int = 5):
    if entry not in G or target not in G:
        return False, []
    queue: deque[tuple[str, list[str], int]] = deque([(entry, [entry], 0)])
    visited: set[str] = set()
    while queue:
        cur, path, depth = queue.popleft()
        if depth > max_depth:
            continue
        if cur in visited:
            continue
        visited.add(cur)
        if cur == target:
            return True, path
        for succ in G.successors(cur):
            queue.append((succ, path + [succ], depth + 1))
    return False, []


def main() -> None:
    G = nx.DiGraph()
    for u, v in [("A", "B"), ("B", "C"), ("C", "A")]:
        G.add_edge(u, v, edge_type="STATIC", confidence=1.0)
    G.nodes["A"]["node_type"] = "FUNCTION"
    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()}")

    data = nx.node_link_data(G, edges="edges")
    H = json_graph.node_link_graph(data, edges="edges")
    assert set(G.nodes) == set(H.nodes)
    print("serialize: OK (node_link round-trip)")

    found, path = bounded_reachable(G, "A", "C", max_depth=5)
    print(f"bfs A->C depth 5: found {found} path {path}")

    G2 = nx.DiGraph()
    G2.add_edge("X", "X", edge_type="STATIC", confidence=1.0)
    found2, _ = bounded_reachable(G2, "X", "X", max_depth=5)
    print(f"self-loop X->X: found {found2} (visited must terminate)")

    # 10k node benchmark
    big = nx.DiGraph()
    start = time.perf_counter()
    for i in range(10000):
        big.add_node(f"n{i}")
    for i in range(9999):
        big.add_edge(f"n{i}", f"n{i+1}", edge_type="STATIC", confidence=1.0)
    elapsed = time.perf_counter() - start
    print(f"10k chain build: {elapsed:.3f}s nodes={big.number_of_nodes()} edges={big.number_of_edges()}")
    assert big.has_node("n0") and big.has_node("n9999")
    print(f"DiGraph collapses parallel: {big['n0']['n1']['edge_type']}")
    # JSON size hint
    raw = json.dumps(nx.node_link_data(big, edges="edges"))
    print(f"serialized size ~{len(raw)//1024} KB")


if __name__ == "__main__":
    main()
