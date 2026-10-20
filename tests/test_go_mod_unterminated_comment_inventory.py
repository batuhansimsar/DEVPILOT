"""Malformed go.mod files should become scan warnings, not empty inventories."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class GoModTruncatedCommentInventoryTests(unittest.TestCase):
    def test_unterminated_comment_is_reported_without_leaking_private_text(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "go.mod").write_text(
                'module example.org/project\n'
                'require example.org/valid v1.0.0\n'
                '/* https://user:secret@example.invalid/private',
                encoding="utf-8",
            )
            report = scan(directory)
        self.assertEqual(report["manifests"], [])
        self.assertEqual(report["totals"], {})
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("unterminated block comment", report["warnings"][0])
        self.assertNotIn("secret", str(report))
        self.assertNotIn("example.invalid", str(report))

    def test_closed_comment_preserves_real_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "go.mod").write_text(
                "module example.org/project\n"
                "/* require example.org/fake v0.0.0 */\n"
                "require example.org/valid v1.0.0\n",
                encoding="utf-8",
            )
            report = scan(directory)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["totals"], {"Go": 1})
        self.assertEqual(report["manifests"][0]["groups"], {"require": ["example.org/valid"]})


if __name__ == "__main__":
    unittest.main()
