"""Pip requirements files may combine environment and purpose qualifiers."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class CombinedRequirementsQualifiersTests(unittest.TestCase):
    def test_combined_prefix_and_suffix_are_manifests(self):
        for name in (
            'dev-requirements-test.txt',
            'test_requirements.local.in',
            'ci.dev-requirements_prod.txt',
            'DEV_REQUIREMENTS_TEST.IN',
            'dev-requirements.txt',
            'requirements-dev.in',
            'requirements.txt',
        ):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_combined_names_do_not_admit_empty_or_spoofed_components(self):
        for name in (
            'dev--requirements-test.txt',
            'dev-requirements--test.in',
            'dev-requirements_.txt',
            'dev_-requirements-test.txt',
            '-requirements-test.txt',
            'dev-requirementsnotes-test.txt',
            'dev-requirements-test.txt.bak',
            'dev-requirements-test.txt.in',
            'dev-requirements-tes\u017ft.txt',
            'dev-requirements-\n.txt',
        ):
            with self.subTest(name=name):
                self.assertFalse(is_requirements_manifest(name))


if __name__ == '__main__':
    unittest.main()
