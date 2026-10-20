"""Keep both Git filename audits aligned on credential-bearing config files."""

import unittest

from devpilot.audit import _potential_secret
from devpilot.secret_audit import classify


class SecretAuditPackageCredentialTests(unittest.TestCase):
    def test_package_and_database_auth_files_are_sensitive_in_both_audits(self):
        paths = (
            'vendor/auth.json', 'home/.pgpass', 'home/.my.cnf',
            'home/.mylogin.cnf', 'frontend/.yarnrc', 'frontend/.yarnrc.yml',
            'infra/.terraformrc', 'infra/credentials.tfrc.json',
            'home/.config/pypoetry/auth.toml', 'home/.config/pip/pip.conf',
            r'C:\Users\developer\pip\pip.ini',
            'project/auth.json.old', 'home/.pgpass.swp',
            'project/.env.production.tmp', 'project/.env.swo',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertIsNotNone(classify(path))

    def test_samples_and_unrelated_configs_are_not_flagged(self):
        paths = (
            'docs/auth.json.example', 'pip/pip.conf.sample',
            'pypoetry/auth.toml.template', 'project/.env.sample.swp',
            'README.md', 'settings/auth.toml', 'src/config.json',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_nested_editor_backups_are_still_sensitive(self):
        for path in ('home/.pgpass', 'frontend/.yarnrc', '.env.production'):
            nested = path + '.swp.tmp.swo.bak' * 5
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(nested))
                self.assertIsNotNone(classify(nested))


if __name__ == '__main__':
    unittest.main()
