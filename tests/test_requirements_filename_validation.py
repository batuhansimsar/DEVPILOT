"""Regressions for pip requirements manifest detection and false positives."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsFilenameValidationTests(unittest.TestCase):
    def test_recognizes_pip_and_pip_tools_conventions(self):
        for name in (
            "requirements.txt", "requirements.in", "requirements-dev.txt",
            "requirements_test.in", "requirements.local.txt",
            "dev-requirements.txt", "test-requirements.in",
            "dev_requirements.txt", "local.requirements.in",
        ):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_rejects_lookalikes_and_empty_qualifiers(self):
        for name in (
            "requirementsbackup.txt", "requirements-dev.ini",
            "requirements-.txt", "requirements_.in", "-requirements.txt",
            "requirements.md", "requirements.txt.bak", "unrelated.in",
            ".requirements.txt", "requirements../backup.txt", "myrequirements.txt",
            "requirements-README", "Requirements.txt", "requirements\n.txt",
        ):
            with self.subTest(name=name):
                self.assertFalse(is_requirements_manifest(name))

    def test_non_string_input_is_not_a_filename(self):
        for value in (None, 123, b"requirements.txt"):
            with self.subTest(value=value):
                self.assertFalse(is_requirements_manifest(value))


if __name__ == "__main__":
    unittest.main()
