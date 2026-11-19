"""Configuration validation, including all six user parameters."""

import json
import tempfile
import unittest
from pathlib import Path

from src.depgraph.config import load_config, split_package
from src.depgraph.errors import AppError


class ConfigTests(unittest.TestCase):
    """Check valid configurations and actionable validation failures."""

    def setUp(self):
        """Create a configuration and a test graph in a temporary folder."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base / "repo.json").write_text('{"A": []}', encoding="utf-8")
        self.data = {
            "package": "A", "repository": "repo.json", "test_mode": True,
            "output": "graph.svg", "ascii_tree": True,
            "filter_substring": "",
        }

    def load(self):
        """Write and load the current test configuration."""
        path = self.base / "config.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        return load_config(path)

    def test_relative_paths(self):
        """Resolve paths relative to the configuration file."""
        config = self.load()
        self.assertEqual(config.output, self.base / "graph.svg")
        self.assertEqual(config.repository, str(self.base / "repo.json"))

    def test_invalid_parameters(self):
        """Reject incorrect values for every user parameter."""
        invalid = {
            "package": ["", 26, "a", "A/B"],
            "repository": ["missing.json", "", 26, "bad\u0000path"],
            "test_mode": ["true", 1, None],
            "output": ["file.png", "", None, "repo.json", "bad\u0000.svg"],
            "ascii_tree": ["false", 0, None],
            "filter_substring": [None, [], "A"],
        }
        for key, values in invalid.items():
            original = self.data[key]
            for value in values:
                with self.subTest(key=key, value=value):
                    self.data[key] = value
                    with self.assertRaises(AppError):
                        self.load()
            self.data[key] = original

    def test_fields_and_invalid_json(self):
        """Reject missing keys, unknown keys and malformed JSON."""
        self.data["extra"] = 1
        with self.assertRaises(AppError):
            self.load()
        del self.data["extra"]
        del self.data["package"]
        with self.assertRaises(AppError):
            self.load()
        path = self.base / "broken.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(AppError):
            load_config(path)

    def test_npm_and_urls(self):
        """Validate npm names, version specs and registry URLs."""
        self.data.update(package="@scope/pkg@^1.0.0", test_mode=False)
        self.data["repository"] = "https://registry.npmjs.org/"
        self.assertFalse(self.load().test_mode)
        self.assertEqual(split_package("@scope/pkg"), ("@scope/pkg", "latest"))
        invalid = ("ftp://host", "https://host:bad", "http://", "http://h?q",
                   "https://[broken")
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(AppError):
                self.data["repository"] = url
                self.load()


if __name__ == "__main__":
    unittest.main()
