"""Regression tests for pip-tools requirements.in dependency inventory."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class RequirementsInputInventoryTests(unittest.TestCase):
    def test_pip_tools_input_and_dev_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.in").write_text(
                "Requests>=2\nmy_pkg[fast] @ https://user:secret@example.test/archive\n"
                "-r shared.in\n--index-url https://user:secret@private.test/simple\n",
                encoding="utf-8",
            )
            (root / "requirements-dev.in").write_text("pytest>=8\n", encoding="utf-8")

            report = scan(root)

        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["totals"]["Python"], 3)
        groups = {entry["path"]: entry["groups"]["requirements"]
                  for entry in report["manifests"]}
        self.assertEqual(groups["requirements.in"], ["my-pkg", "requests"])
        self.assertEqual(groups["requirements-dev.in"], ["pytest"])
        self.assertNotIn("secret", json.dumps(report))
        self.assertNotIn("private.test", json.dumps(report))

    def test_existing_requirements_txt_still_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "requirements.txt").write_text("Flask==3.0\n", encoding="utf-8")
            report = scan(root)

        self.assertEqual(report["totals"]["Python"], 1)
        self.assertEqual(report["manifests"][0]["groups"]["requirements"], ["flask"])

    def test_unrelated_input_file_not_included(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "constraints.in").write_text("requests==2\n", encoding="utf-8")
            report = scan(root)

        self.assertEqual(report["manifests"], [])
        self.assertEqual(report["totals"], {})


if __name__ == "__main__":
    unittest.main()
