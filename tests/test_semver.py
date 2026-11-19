"""Version selection cases covering common npm range syntax."""

import unittest

from src.depgraph.errors import AppError
from src.depgraph.semver import Version, select_version


class SemverTests(unittest.TestCase):
    """Verify bounds, prereleases and unsupported requirement errors."""

    def test_ranges(self):
        """Select the highest matching version for each range kind."""
        versions = ["0.0.2", "0.0.3", "0.2.3", "0.3.0", "1.0.0",
                    "1.2.0", "1.2.3", "1.3.0", "2.0.0", "2.1.0"]
        cases = {
            "^1.2.0": "1.3.0", "~1.2.0": "1.2.3", "1.2.x": "1.2.3",
            ">=1 <2": "1.3.0", "1.0 - 1.2": "1.2.3", "*": "2.1.0",
            "^0.2.3": "0.2.3", "^0.0.2": "0.0.2", "~1": "1.3.0",
            "<=1.2": "1.2.3", ">1": "2.1.0", "1 || 2": "2.1.0",
        }
        for spec, expected in cases.items():
            with self.subTest(spec=spec):
                self.assertEqual(select_version(versions, spec, {}), expected)

    def test_prereleases(self):
        """Admit prereleases only for an explicitly mentioned core."""
        versions = ["1.0.0", "1.1.0-beta.2", "1.1.0-beta.10", "2.0.0-beta"]
        self.assertEqual(select_version(versions, "*", {}), "1.0.0")
        self.assertEqual(select_version(versions, ">=1.1.0-beta.1 <2", {}),
                         "1.1.0-beta.10")
        self.assertLess(Version.parse("1.0.0-1"), Version.parse("1.0.0-a"))
        self.assertLess(Version.parse("1.0.0-a"), Version.parse("1.0.0"))

    def test_tags_and_errors(self):
        """Honor dist-tags and fail visibly for unsupported requirements."""
        self.assertEqual(select_version(["1.0.0"], "latest",
                                        {"latest": "1.0.0"}), "1.0.0")
        for spec in ("^3.0.0", "git+https://host/repo", "file:../a"):
            with self.subTest(spec=spec), self.assertRaises(AppError):
                select_version(["1.0.0"], spec, {})
