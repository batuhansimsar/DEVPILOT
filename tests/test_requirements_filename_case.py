"""Case-insensitive pip manifest discovery without Unicode spoofing."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsFilenameCaseTests(unittest.TestCase):
    def test_uppercase_and_mixed_case_manifest_names(self):
        for name in (
            "REQUIREMENTS.TXT",
            "Requirements-Dev.TXT",
            "DEV-REQUIREMENTS.IN",
            "requirements.Test.in",
            "Requirements_Prod.Txt",
        ):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_rejects_lookalikes_and_unicode_casefold_aliases(self):
        for name in (
            "requirementsbackup.txt",
            "REQUIREMENTS-.TXT",
            "foo.txt",
            "requ\u0131rements.txt",  # dotless i
            "requ\u0130rements.txt",  # uppercase dotted I
            "requirement\u017f.txt",  # long s
            "requirements\uff0etxt",  # fullwidth dot
            "REQUIREMENTS.TXT.TXT",  # duplicate extension in uppercase
            "Requirements.In.TxT",  # mixed-case duplicate extension
        ):
            with self.subTest(name=name):
                self.assertFalse(is_requirements_manifest(name))

    def test_non_string_input_remains_invalid(self):
        for value in (None, 1, b"requirements.txt"):
            with self.subTest(value=value):
                self.assertFalse(is_requirements_manifest(value))


if __name__ == "__main__":
    unittest.main()
