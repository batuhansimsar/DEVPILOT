"""Regression coverage for Git and GitHub CLI credential file detection."""

import unittest

from devpilot.secret_audit import classify


class GitCredentialStorageTests(unittest.TestCase):
    def test_git_plaintext_credential_store_and_backups(self):
        for path in (
            '.git-credentials',
            'nested/.git-credentials',
            'NESTED\\.GIT-CREDENTIALS.BAK',
            '.git-credentials.old',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential file')

    def test_github_cli_yaml_credentials_and_backups(self):
        for path in (
            '.config/gh/hosts.yaml',
            'nested/.config/gh/hosts.yml',
            'NESTED\\.CONFIG\\GH\\HOSTS.YAML.BACKUP',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_templates_and_unrelated_hosts_files_are_safe(self):
        for path in (
            '.git-credentials.example',
            '.git-credentials.sample.bak',
            '.config/gh/hosts.yaml.template',
            'docs/hosts.yaml',
            '.config/git/hosts.yaml',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))


if __name__ == '__main__':
    unittest.main()
