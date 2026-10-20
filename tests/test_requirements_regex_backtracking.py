"""Adversarial filenames must not trigger catastrophic regex backtracking."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsRegexBacktrackingTests(unittest.TestCase):
    def test_long_repeated_qualifiers_are_accepted(self):
        filename = 'requirements-' + 'a-' * 70 + 'final.txt'
        self.assertTrue(is_requirements_manifest(filename))

    def test_long_repeated_qualifiers_with_invalid_tail_are_rejected(self):
        # This fits common 255-byte filesystem filename limits but caused
        # exponential backtracking in the previous nested regex repetition.
        filename = 'requirements-' + 'a-' * 70 + '!.txt'
        self.assertFalse(is_requirements_manifest(filename))

    def test_invalid_empty_components_do_not_match(self):
        for filename in ('requirements-dev_.txt', 'requirements-dev--test.txt',
                         'requirements-dev__test.in', 'requirements-dev-.in'):
            with self.subTest(filename=filename):
                self.assertFalse(is_requirements_manifest(filename))

    def test_multiple_valid_separators_still_match(self):
        for filename in ('requirements-dev_prod.local.txt',
                         'requirements-1.2_rc.in', 'dev_test-requirements.txt'):
            with self.subTest(filename=filename):
                self.assertTrue(is_requirements_manifest(filename))


if __name__ == '__main__':
    unittest.main()
