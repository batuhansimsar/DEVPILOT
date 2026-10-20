"""Regression coverage for credential paths discovered by the Git index audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class CloudCredentialAuditTests(unittest.TestCase):
    def test_sensitive_cloud_cli_paths(self):
        for name in (
            'application_default_credentials.json',
            'profile/.azure/accessTokens.json',
            '.azure/msal_token_cache.json',
            '.azure/msal_token_cache.bin',
            'profile/.config/gh/hosts.yml',
            'C:\\Users\\me\\.Azure\\accessTokens.json',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_generic_configs_and_templates_not_reported(self):
        for name in (
            'docs/hosts.yml', '.config/gh/config.yml',
            'config/msal_token_cache.json', 'src/accessTokens.json',
            '.azure/README.md', '.config/git/hosts.yml',
            'application_default_credentials.json.example',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_cloud_credentials_appear_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            staged = ('.azure/msal_token_cache.json', '.config/gh/hosts.yml',
                      'application_default_credentials.json', 'docs/hosts.yml')
            for name in (*staged, 'untracked.key'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('DO_NOT_LEAK_CREDENTIAL_VALUE', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *staged], cwd=root, check=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 4)
        self.assertEqual(report['candidates'], [
            '.azure/msal_token_cache.json', '.config/gh/hosts.yml',
            'application_default_credentials.json',
        ])
        self.assertNotIn('DO_NOT_LEAK_CREDENTIAL_VALUE', repr(report))
        self.assertNotIn('untracked.key', repr(report))


if __name__ == '__main__':
    unittest.main()
