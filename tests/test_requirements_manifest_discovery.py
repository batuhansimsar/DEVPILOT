"""Regression tests for requirements-*.txt and requirements-*.in project discovery."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import detect_projects, test_commands


class RequirementsManifestDiscoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_alternative_requirements_files_identify_python_project(self):
        for name in ("requirements-dev.txt", "requirements.in", "requirements-test.in"):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text("pytest\n", encoding="utf-8")
                self.assertIn("Python", detect_projects(self.root))
                path.unlink()

    def test_alternative_requirements_files_discover_tests(self):
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_example.py").touch()
        (self.root / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
        with patch("devpilot.python_tests.PathFinder.find_spec", return_value=object()):
            commands = test_commands(self.root)
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["ecosystem"], "Python")
        self.assertEqual(commands[0]["argv"], [sys.executable, "-m", "pytest", "tests"])

    def test_unittest_fallback_and_no_test_directory(self):
        (self.root / "requirements.in").write_text("requests\n", encoding="utf-8")
        self.assertEqual(test_commands(self.root), [])
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_example.py").touch()
        with patch("devpilot.python_tests.PathFinder.find_spec", return_value=None):
            commands = test_commands(self.root)
        self.assertEqual(len(commands), 1)
        self.assertEqual(
            commands[0]["argv"],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        )

    def test_lookalike_manifest_does_not_count(self):
        (self.root / "requirements.md").write_text("notes", encoding="utf-8")
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_example.py").touch()
        self.assertNotIn("Python", detect_projects(self.root))
        self.assertEqual(test_commands(self.root), [])

    def test_does_not_use_symlinked_test_directory(self):
        (self.root / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
        (self.root / "real_tests").mkdir()
        try:
            (self.root / "tests").symlink_to(self.root / "real_tests", target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unsupported")
        self.assertEqual(test_commands(self.root), [])


if __name__ == "__main__":
    unittest.main()
