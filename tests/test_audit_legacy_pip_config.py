"""Regression checks for legacy pip credential-bearing configuration paths."""

import unittest

from devpilot.audit import _potential_secret
from devpilot.secret_audit import classify


class LegacyPipConfigTests(unittest.TestCase):
    def test_legacy_pip_configuration_is_flagged_by_both_auditors(self):
        for path in (
            '.pip/pip.conf',
            'home/.pip/pip.conf',
            r'HOME\\.PIP\\PIP.CONF',
            'home/.pip/pip.conf.bak',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_templates_and_unrelated_configs_are_not_flagged(self):
        for path in (
            '.pip/pip.conf.example',
            'home/.pip/pip.conf.template',
            'docs/pip.conf',
            'pip.conf',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))


if __name__ == '__main__':
    unittest.main()
