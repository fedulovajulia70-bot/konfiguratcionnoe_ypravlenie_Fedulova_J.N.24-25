"""Compute a dependencies-first order for acyclic graphs."""

from .errors import AppError


def load_order(graph):
    """Return DFS postorder; refuse to invent an order for a cyclic graph."""
    if graph.cycles:
        cycle = " -> ".join(graph.cycles[0])
        raise AppError(f"Load order is impossible: dependency cycle {cycle}")
    order = []
    visited = set()

    def visit(key):
        """Append a package only after all its dependencies."""
        if key in visited:
            return
        visited.add(key)
        for child in graph.edges[key]:
            visit(child)
        order.append(key)

    visit(graph.root)
    return order
