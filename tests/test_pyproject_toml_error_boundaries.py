"""TOML parser failures must not expose untrusted manifest diagnostics."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import scan
from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectTomlErrorBoundaryTests(unittest.TestCase):
    def test_numeric_parser_errors_are_sanitized(self):
        for error_type in (ValueError, OverflowError):
            with self.subTest(error=error_type.__name__):
                with patch(
                    "devpilot.pyproject_deps.tomllib.loads",
                    side_effect=error_type("private-token=topsecret"),
                ):
                    with self.assertRaises(ValueError) as caught:
                        parse_pyproject_dependencies("[project]\nname = 'safe'\n")
                self.assertEqual(str(caught.exception), "Invalid pyproject.toml TOML")
                self.assertTrue(caught.exception.__suppress_context__)
                self.assertNotIn("topsecret", str(caught.exception))

    def test_oversized_integer_is_reported_privately_by_inventory(self):
        # Python and tomli may enforce an integer digit limit; either outcome
        # must be a sanitized warning, never the raw numeric parser error.
        payload = "[project]\nprivate_counter = " + "9" * 5000
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "pyproject.toml").write_text(payload, encoding="utf-8")
            report = scan(directory)
        # On runtimes that permit arbitrary-size integers, the unused metadata
        # is valid and may simply produce an empty dependency inventory.
        if report["warnings"]:
            self.assertEqual(report["warnings"], [
                "pyproject.toml: Invalid pyproject.toml TOML"
            ])
            self.assertNotIn("private_counter", str(report["warnings"]))
        else:
            self.assertEqual(report["manifests"][0]["groups"], {})

    def test_normal_numeric_metadata_does_not_affect_dependency_inventory(self):
        self.assertEqual(
            parse_pyproject_dependencies(
                "[project]\nprivate_counter = 42\ndependencies = ['requests>=2']\n"
            ),
            {"dependencies": ["requests"]},
        )


if __name__ == "__main__":
    unittest.main()
