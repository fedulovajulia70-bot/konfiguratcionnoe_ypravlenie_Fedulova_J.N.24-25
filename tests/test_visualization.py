"""Check graph serialization and renderer failures without requiring D2."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.depgraph.errors import AppError
from src.depgraph.graph import build_graph
from src.depgraph.repository import TestRepository
from src.depgraph.visualization import ascii_tree, export_graph, to_d2

REPOSITORIES = Path(__file__).parents[1] / "examples/repositories"


def fixture(name):
    """Build a versionless graph for output assertions."""
    repository = TestRepository(REPOSITORIES / f"{name}.json")
    return build_graph(repository, repository.resolve("A"))


class VisualizationTests(unittest.TestCase):
    """Preserve graph structure and terminate ASCII output on revisits."""

    def test_d2_edges_and_isolated_root(self):
        """Include each edge and isolated node in the D2 source."""
        text = to_d2(fixture("diamond"))
        self.assertEqual(text.count(" -> "), 4)
        self.assertIn('n0: "A"', text)
        self.assertIn('n0: "A"', to_d2(fixture("isolated")))

    def test_ascii_shared_and_cycle(self):
        """Mark a reused subtree separately from a recursion-stack cycle."""
        self.assertEqual(ascii_tree(fixture("diamond")),
                         "A\n|-- B\n|   `-- D\n`-- C\n    `-- D [shared]")
        self.assertIn("A [cycle]", ascii_tree(fixture("cycle")))
        self.assertEqual(ascii_tree(fixture("isolated")), "A")

    def test_successful_export(self):
        """Validate the SVG returned by an isolated renderer subprocess."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"

            def render(*args, **kwargs):
                """Stand in for D2 without testing its own implementation."""
                output.write_text(
                    '<svg xmlns="http://www.w3.org/2000/svg"/>',
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(args, 0, "", "")

            with patch("src.depgraph.visualization.find_d2") as locate:
                locate.return_value = "d2"
                with patch("src.depgraph.visualization.subprocess.run",
                           side_effect=render):
                    source, image = export_graph(fixture("diamond"), output)
            self.assertTrue(source.is_file())
            self.assertEqual(image, output)

    def test_renderer_error_keeps_source(self):
        """Report renderer failures and preserve reusable D2 source."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "graph.svg"
            result = subprocess.CompletedProcess([], 1, "", "bad diagram")
            with patch("src.depgraph.visualization.find_d2") as locate:
                locate.return_value = "d2"
                with patch("src.depgraph.visualization.subprocess.run",
                           return_value=result):
                    with self.assertRaisesRegex(AppError, "bad diagram"):
                        export_graph(fixture("diamond"), output)
            self.assertTrue(output.with_suffix(".d2").is_file())
