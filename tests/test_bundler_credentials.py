"""Regression coverage for Bundler credential-bearing configuration paths."""

import unittest

from devpilot.bundler_credentials import is_bundler_credential_location


class BundlerCredentialLocationTests(unittest.TestCase):
    def test_conventional_paths_are_sensitive(self):
        for parts in (
            ('.bundle', 'config'),
            ('project', '.bundle', 'config'),
            ('home', 'user', '.bundle', 'config'),
        ):
            with self.subTest(parts=parts):
                self.assertTrue(is_bundler_credential_location(parts))

    def test_generic_config_and_templates_are_ignored(self):
        for parts in (
            (), ('config',), ('.bundle',),
            ('config', 'config'), ('bundle', 'config'),
            ('.bundle', 'config.example'),
            ('.bundle', 'config.sample'),
            ('docs', 'config'), ('project', '.bundle', 'credentials'),
        ):
            with self.subTest(parts=parts):
                self.assertFalse(is_bundler_credential_location(parts))


if __name__ == '__main__':
    unittest.main()
