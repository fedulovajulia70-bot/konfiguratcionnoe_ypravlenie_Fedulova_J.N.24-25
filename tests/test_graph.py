"""Graph correctness for cycles, shared subgraphs and filtering."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from src.depgraph.errors import AppError
from src.depgraph.graph import build_graph
from src.depgraph.operations import load_order
from src.depgraph.repository import Package, TestRepository

REPOSITORIES = Path(__file__).parents[1] / "examples/repositories"


def graph_for(name, excluded=""):
    """Build a fixture graph starting at A."""
    repository = TestRepository(REPOSITORIES / f"{name}.json")
    return build_graph(repository, repository.resolve("A"), excluded)


class GraphTests(unittest.TestCase):
    """Verify recursive DFS results independently of formatting."""

    def test_diamond(self):
        """Preserve both incoming edges of a shared dependency."""
        graph = graph_for("diamond")
        self.assertEqual(graph.edges, {
            "A": ["B", "C"], "B": ["D"], "D": [], "C": ["D"],
        })
        self.assertEqual(graph.cycles, [])

    def test_cycles(self):
        """Retain cycle edges and terminate for cycles and self-loops."""
        graph = graph_for("cycle")
        self.assertEqual(graph.cycles, [("A", "B", "C", "A")])
        self.assertEqual(graph.edges["C"], ["A", "D"])
        graph = graph_for("self-cycle")
        self.assertEqual(graph.edges, {"A": ["A"]})
        self.assertEqual(graph.cycles, [("A", "A")])

    def test_filtered_and_isolated(self):
        """Prune filtered branches and retain a root without dependencies."""
        graph = graph_for("diamond", "B")
        self.assertEqual(graph.edges, {"A": ["C"], "C": ["D"], "D": []})
        self.assertEqual(graph_for("isolated").edges, {"A": []})
        self.assertEqual(graph_for("chain", "B").edges, {"A": []})

    def test_filter_before_network(self):
        """Do not fetch a dependency whose name is excluded."""
        repository = Mock()
        root = Package("root", "1.0.0", {"skip-me": "*"})
        graph = build_graph(repository, root, "skip")
        repository.resolve.assert_not_called()
        self.assertEqual(graph.edges, {"root@1.0.0": []})

    def test_multiple_versions(self):
        """Keep different versions of one name as different nodes."""
        packages = {
            ("b", "1.0.0"): Package("b", "1.0.0", {}),
            ("c", "1.0.0"): Package("c", "1.0.0", {"b": "2.0.0"}),
            ("b", "2.0.0"): Package("b", "2.0.0", {}),
        }
        repository = Mock()
        repository.resolve.side_effect = lambda n, s: packages[n, s]
        root = Package("a", "1.0.0", {"b": "1.0.0", "c": "1.0.0"})
        graph = build_graph(repository, root)
        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(graph.edges["c@1.0.0"], ["b@2.0.0"])

    def test_load_order(self):
        """Every dependency precedes every package depending on it."""
        for name in ("diamond", "chain", "isolated"):
            with self.subTest(name=name):
                graph = graph_for(name)
                order = load_order(graph)
                self.assertEqual(set(order), set(graph.nodes))
                for parent, children in graph.edges.items():
                    for child in children:
                        self.assertLess(
                            order.index(child), order.index(parent),
                        )
        self.assertEqual(
            load_order(graph_for("diamond")), ["D", "B", "C", "A"],
        )

    def test_cyclic_load_order(self):
        """Reject a cycle instead of presenting a misleading partial order."""
        for name in ("cycle", "self-cycle"):
            with self.subTest(name=name), self.assertRaises(AppError):
                load_order(graph_for(name))
