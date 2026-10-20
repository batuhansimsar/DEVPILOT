"""uv.lock inventory must not disclose private index credentials or metadata."""

import tempfile
import unittest
from pathlib import Path

from devpilot.uv_lock import parse_uv_lock


class UvLockTests(unittest.TestCase):
    def test_normalizes_and_deduplicates_without_exposing_private_sources(self):
        content = '''version = 1
requires-python = ">=3.10"
[[package]]
name = "My_Pkg"
version = "1.2.3"
source = { registry = "https://user:secret@example.invalid/simple" }
[[package]]
name = "my-pkg"
version = "1.2.4"
[[package]]
name = "Requests"
version = "2.32.0"
'''
        result = parse_uv_lock(content)
        self.assertEqual(result, ["my-pkg", "requests"])
        self.assertNotIn("secret", str(result))
        self.assertNotIn("example.invalid", str(result))

    def test_empty_lockfile(self):
        self.assertEqual(parse_uv_lock("version = 1\n"), [])
        self.assertEqual(parse_uv_lock("package = []\n"), [])

    def test_invalid_package_records_are_rejected_without_echoing_values(self):
        for value in (
            'package = "bad"\n',
            'package = ["bad"]\n',
            '[[package]]\nversion = "1.0"\n',
            '[[package]]\nname = "https://user:secret@example.invalid"\n',
            '[[package]]\nname = 100\n',
            '[[package]]\nname = "invalid name"\n',
            '[[package]]\nname = "bad\\u0000name"\n',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError) as raised:
                parse_uv_lock(value)
            self.assertNotIn("secret", str(raised.exception))
            self.assertNotIn("https", str(raised.exception))

    def test_invalid_toml_does_not_expose_source(self):
        with self.assertRaisesRegex(ValueError, r"invalid uv.lock TOML") as raised:
            parse_uv_lock('source = "https://user:secret@example.invalid"\nbroken = [\n')
        self.assertNotIn("secret", str(raised.exception))

    def test_scan_integration(self):
        from devpilot.deps import scan
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "uv.lock").write_text(
                'version = 1\n[[package]]\nname = "httpx"\nversion = "0.28.0"\n'
                '[[package]]\nname = "pydantic_Core"\nversion = "2.0"\n',
                encoding="utf-8",
            )
            report = scan(root)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["totals"], {"Python": 2})
        self.assertEqual(report["manifests"][0]["path"], "uv.lock")
        self.assertEqual(report["manifests"][0]["groups"], {
            "locked": ["httpx", "pydantic-core"],
        })


if __name__ == "__main__":
    unittest.main()
