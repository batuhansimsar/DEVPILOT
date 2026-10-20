"""Case-insensitive pip manifest detection for multi-platform workspaces."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsCaseVariantsTests(unittest.TestCase):
    def test_case_insensitive_standard_and_pip_tools_names(self):
        for name in (
            'requirements.txt', 'REQUIREMENTS.TXT', 'Requirements.In',
            'Requirements-DEV.TxT', 'REQUIREMENTS-Test.IN',
            'TEST-REQUIREMENTS.TXT', 'Dev-Requirements.In',
        ):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_does_not_accept_unrelated_names_or_extensions(self):
        for name in (
            'requirements.md', 'REQUIREMENTS.INI', 'requirements.txt.bak',
            'REQUIREMENTS.TXT.TXT', 'requirementsnotes.txt',
            'otherrequirements.txt', 'requirements', 'test-requirements.md',
            '-requirements.txt', '-requirements.in', 'requirements-config.yaml',
        ):
            with self.subTest(name=name):
                # The bare suffix-only form should not be treated as a manifest.
                self.assertFalse(is_requirements_manifest(name))


if __name__ == '__main__':
    unittest.main()
