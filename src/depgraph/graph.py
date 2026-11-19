"""Construct the full dependency graph using recursive depth-first search."""

from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    """Resolved packages, adjacency lists and discovered back-edge cycles."""

    root: str
    nodes: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)


def build_graph(repository, root, excluded=""):
    """Recursively visit dependencies, pruning filtered names before fetching."""
    graph = DependencyGraph(root.key)
    active = []

    def visit(package):
        """DFS with a recursion stack and a set of previously visited nodes."""
        key = package.key
        if key in active:
            graph.cycles.append(tuple(active[active.index(key):] + [key]))
            return
        if key in graph.nodes:
            return
        graph.nodes[key] = package
        graph.edges[key] = []
        active.append(key)
        for name, spec in sorted(package.dependencies.items()):
            if excluded and excluded in name:
                continue
            child = repository.resolve(name, spec)
            if excluded and excluded in child.name:
                continue
            graph.edges[key].append(child.key)
            visit(child)
        active.pop()

    visit(root)
    return graph


def describe_graph(graph):
    """Return a deterministic adjacency list, including isolated nodes."""
    return "\n".join(
        f"{key}: {', '.join(children) or '(none)'}"
        for key, children in graph.edges.items()
    )
