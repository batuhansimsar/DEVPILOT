"""Cargo's registry token stores are recognized without broad false positives."""

import unittest

from devpilot.cargo_credentials import is_cargo_credential_location


class CargoCredentialPathTests(unittest.TestCase):
    def test_current_and_legacy_credential_files(self):
        for path in (
            ('.cargo', 'credentials.toml'),
            ('.cargo', 'credentials'),
            ('home', 'user', '.cargo', 'credentials.toml'),
        ):
            with self.subTest(path=path):
                self.assertTrue(is_cargo_credential_location(path))

    def test_unrelated_cargo_files_and_generic_credentials_are_ignored(self):
        for path in (
            ('credentials.toml',),
            ('docs', 'credentials.toml'),
            ('.cargo', 'config.toml'),
            ('.cargo', 'credentials.toml.example'),
            ('cargo', 'credentials.toml'),
        ):
            with self.subTest(path=path):
                self.assertFalse(is_cargo_credential_location(path))


if __name__ == '__main__':
    unittest.main()
