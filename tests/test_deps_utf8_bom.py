"""Regression tests for UTF-8 BOM-prefixed dependency manifests."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class UTF8BOMDependencyTests(unittest.TestCase):
    def test_node_manifest_with_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_bytes(
                b'\xef\xbb\xbf{"dependencies":{"react":"^18"},"devDependencies":{"vitest":"^2"}}'
            )
            report = scan(root)
            self.assertEqual(report["totals"], {"Node.js": 2})
            self.assertEqual(report["manifests"][0]["groups"], {
                "dependencies": ["react"], "devDependencies": ["vitest"],
            })
            self.assertEqual(report["warnings"], [])

    def test_composer_manifest_with_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composer.json").write_bytes(
                b'\xef\xbb\xbf{"require":{"psr/log":"^3"},"require-dev":{"phpunit/phpunit":"^11"}}'
            )
            report = scan(root)
            self.assertEqual(report["totals"], {"PHP": 2})
            self.assertEqual(report["manifests"][0]["groups"], {
                "require": ["psr/log"], "require-dev": ["phpunit/phpunit"],
            })
            self.assertEqual(report["warnings"], [])

    def test_bom_requirements_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_bytes(b"\xef\xbb\xbfrequests>=2\n")
            report = scan(root)
            self.assertEqual(report["totals"], {"Python": 1})
            self.assertEqual(report["manifests"][0]["groups"]["requirements"], ["requests"])
            self.assertEqual(report["warnings"], [])

    def test_invalid_utf8_after_bom_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_bytes(b'\xef\xbb\xbf{"secret":"private-value\xff"}')
            report = scan(root)
            self.assertEqual(report["manifests"], [])
            self.assertEqual(len(report["warnings"]), 1)
            self.assertNotIn("private-value", str(report))


if __name__ == "__main__":
    unittest.main()
