"""Malformed TOML must not crash direct lockfile parsers or reveal values."""

import unittest
from unittest.mock import patch

from devpilot.poetry_lock import parse_poetry_lock
from devpilot.uv_lock import parse_uv_lock


class TomlLockParserLimitTests(unittest.TestCase):
    def test_integer_conversion_errors_are_private(self):
        # Conversion limits vary by runtime: mock a deterministic parser error.
        for module, parser, label in (
            ("devpilot.poetry_lock", parse_poetry_lock, "poetry.lock"),
            ("devpilot.uv_lock", parse_uv_lock, "uv.lock"),
        ):
            with self.subTest(parser=label), patch(
                module + ".tomllib.loads", side_effect=ValueError("private metadata")
            ):
                with self.assertRaisesRegex(ValueError, "^invalid " + label.replace(".", r"\.") + " TOML$") as raised:
                    parser("")
                self.assertNotIn("private metadata", str(raised.exception))

    def test_excessive_nesting_is_sanitized(self):
        content = 'source = "private metadata"\nnested = ' + "[" * 2500 + "0" + "]" * 2500
        for parser, label in ((parse_poetry_lock, "poetry.lock"),
                              (parse_uv_lock, "uv.lock")):
            with self.subTest(parser=label), self.assertRaisesRegex(
                ValueError, "^invalid " + label.replace(".", r"\.") + " TOML$"
            ) as raised:
                parser(content)
            self.assertNotIn("private metadata", str(raised.exception))

    def test_numeric_overflow_errors_are_private(self):
        for module, parser, label in (
            ("devpilot.poetry_lock", parse_poetry_lock, "poetry.lock"),
            ("devpilot.uv_lock", parse_uv_lock, "uv.lock"),
        ):
            with self.subTest(parser=label), patch(
                module + ".tomllib.loads", side_effect=OverflowError("private metadata")
            ):
                with self.assertRaisesRegex(ValueError, "^invalid " + label.replace(".", r"\.") + " TOML$") as raised:
                    parser("")
                self.assertNotIn("private metadata", str(raised.exception))

    def test_valid_lockfiles_still_work(self):
        for parser in (parse_poetry_lock, parse_uv_lock):
            with self.subTest(parser=parser.__name__):
                result = parser('[[package]]\nname = "My_Pkg"\nversion = "1.0"\n')
                self.assertEqual(result, ["my-pkg"])


if __name__ == "__main__":
    unittest.main()
