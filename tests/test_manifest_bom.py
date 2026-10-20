"""Regression tests for package.json files saved with a UTF-8 BOM."""

import tempfile
import unittest
from pathlib import Path

from devpilot.manifest import read_package_json


class ManifestBOMTests(unittest.TestCase):
    def test_utf8_bom_is_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_bytes(
                b'\\xef\\xbb\\xbf{"name":"example","scripts":{"test":"node --test"}}'
            )
            package, error = read_package_json(root)
            self.assertIsNone(error)
            self.assertEqual(package["name"], "example")
            self.assertEqual(package["scripts"]["test"], "node --test")

    def test_invalid_utf8_still_rejected_without_dumping_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_bytes(b'\\xef\\xbb\\xbf{"secret":"\\xff"}')
            package, error = read_package_json(root)
            self.assertIsNone(package)
            self.assertEqual(error, "Invalid package.json: must be UTF-8")


if __name__ == "__main__":
    unittest.main()
