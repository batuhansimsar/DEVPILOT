"""Regression coverage for underscore- and period-prefixed pip requirements manifests."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class UnderscoredRequirementsTests(unittest.TestCase):
    def test_common_underscored_prefixes_are_recognized(self):
        for filename in (
            'dev_requirements.txt',
            'test_requirements.in',
            'production_requirements.txt',
            'ci_build_requirements.in',
            'local.requirements.in',
            'ci.build_requirements.txt',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_requirements_manifest(filename))

    def test_unrelated_or_unsafe_lookalikes_remain_excluded(self):
        for filename in (
            '_requirements.txt',
            'bad..requirements.txt',
            'bad.requirements.md',
            'dev_requirements.md',
            'myrequirements.txt',
            'test_requirements.txt.bak',
            'dev_requirements.txt.txt',
            'dev_requirements.in.txt',
            'dev_requirements',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_requirements_manifest(filename))


if __name__ == '__main__':
    unittest.main()
