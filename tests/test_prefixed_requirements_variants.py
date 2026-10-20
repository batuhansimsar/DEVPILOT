"""Qualified prefixed requirements files are valid pip input manifests."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class PrefixedRequirementsVariantsTests(unittest.TestCase):
    def test_prefixed_requirements_with_qualifiers_are_recognized(self):
        for filename in (
            'dev-requirements-ci.txt',
            'test_requirements_local.in',
            'integration.requirements-prod.txt',
            'dev_test-requirements-py312.in',
            'DEV-REQUIREMENTS-LOCAL.TXT',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_requirements_manifest(filename))

    def test_empty_or_malformed_qualifiers_are_rejected(self):
        for filename in (
            'dev-requirements-.txt',
            'test_requirements__local.txt',
            'dev-requirements..prod.txt',
            'dev-requirements-ci.txt.bak',
            'dev-requirements-ci.txt.txt',
            'dev--requirements-ci.txt',
            'dev-requirements\nci.txt',
            'dev-requirements-K.txt',
            'dev-requirements-ſ.txt',
            'requirementsnotes-ci.txt',
            'dev-requirements-ci.md',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_requirements_manifest(filename))

    def test_long_prefixed_qualifiers_have_bounded_matching(self):
        prefix = 'dev-requirements-' + 'a-' * 70
        self.assertTrue(is_requirements_manifest(prefix + 'final.txt'))
        self.assertFalse(is_requirements_manifest(prefix + '!.txt'))

    def test_unqualified_names_keep_their_existing_behavior(self):
        self.assertTrue(is_requirements_manifest('requirements.txt'))
        self.assertTrue(is_requirements_manifest('dev-requirements.txt'))
        self.assertFalse(is_requirements_manifest('myrequirements.txt'))


if __name__ == '__main__':
    unittest.main()
