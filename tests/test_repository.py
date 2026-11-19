"""Test registry parsing without accessing the network."""

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from src.depgraph.errors import AppError
from src.depgraph.repository import NpmRepository, TestRepository


class RepositoryTests(unittest.TestCase):
    """Exercise cached requests, version selection and invalid responses."""

    def test_registry_and_cache(self):
        """Resolve dependencies from raw npm JSON with one HTTP request."""
        data = {
            "dist-tags": {"latest": "1.2.0"},
            "versions": {"1.2.0": {"dependencies": {"b": "^2.0.0"}}},
        }
        with patch("src.depgraph.repository.urlopen") as fetch:
            fetch.return_value = io.BytesIO(json.dumps(data).encode())
            repository = NpmRepository("https://registry.npmjs.org")
            package = repository.resolve("@scope/a")
            self.assertEqual(package.key, "@scope/a@1.2.0")
            self.assertEqual(package.dependencies, {"b": "^2.0.0"})
            repository.resolve("@scope/a")
            self.assertEqual(fetch.call_count, 1)
            url = fetch.call_args.args[0].full_url
            self.assertTrue(url.endswith("@scope%2Fa"))

    def test_network_and_metadata_errors(self):
        """Wrap network errors and reject invalid JSON structures."""
        repository = NpmRepository("https://registry.npmjs.org")
        with patch("src.depgraph.repository.urlopen") as fetch:
            fetch.side_effect = URLError("x")
            with self.assertRaises(AppError):
                repository.resolve("missing")
        for body in (b"bad", b"[]", b'{}', b'{"versions": []}'):
            with self.subTest(body=body):
                with patch("src.depgraph.repository.urlopen") as fetch:
                    fetch.return_value = io.BytesIO(body)
                    with self.assertRaises(AppError):
                        repository.resolve("a")

    def test_invalid_dependency_map(self):
        """Reject malformed manifest dependency values."""
        repository = NpmRepository("https://registry.npmjs.org")
        repository.cache["a"] = {
            "versions": {"1.0.0": {"dependencies": {"b": 42}}},
        }
        with self.assertRaises(AppError):
            repository.resolve("a", "1.0.0")

    def test_test_repository(self):
        """Read a diamond graph and report an absent root."""
        path = Path(__file__).parents[1] / "examples/repositories/diamond.json"
        repository = TestRepository(path)
        self.assertEqual(
            repository.resolve("A").dependencies, {"B": "*", "C": "*"},
        )
        with self.assertRaises(AppError):
            repository.resolve("Z")
