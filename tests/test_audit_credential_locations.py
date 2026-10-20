"""Regression checks for credential-bearing Git paths in the CLI audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class CredentialLocationTests(unittest.TestCase):
    def test_sensitive_filenames_and_well_known_locations(self):
        for name in (
            '.aws/credentials', 'project/.aws/credentials',
            '.kube/config', 'home/.docker/config.json',
            'PROJECT\\.AWS\\CREDENTIALS',
            '.envrc', '.netrc', 'credentials.json', 'secrets.json',
            'service_account.json', 'google-credentials.json', 'signing.jks',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_generic_config_and_templates_are_not_flagged(self):
        for name in (
            'src/config.json', 'src/config', 'src/credentials.py',
            '.aws/credentials.example', '.kube/config.sample',
            '.docker/config.json.template', '.env.example',
            '.env.production.sample', 'id_ed25519.pub', 'README.md',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_audit_reports_only_tracked_sensitive_config_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('.aws/credentials', '.kube/config', '.docker/config.json',
                         'src/config.json', '.aws/credentials.example', 'untracked.jks'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('fixture-content-should-not-be-reported', encoding='utf-8')
            subprocess.run(['git', 'add', '--', '.aws/credentials', '.kube/config',
                            '.docker/config.json', 'src/config.json',
                            '.aws/credentials.example'], cwd=root, check=True)
            result = audit_tracked_files(root)
        self.assertNotIn('error', result)
        self.assertEqual(result['tracked_files'], 5)
        self.assertEqual(result['candidates'], ['.aws/credentials', '.docker/config.json', '.kube/config'])
        self.assertNotIn('fixture-content', str(result))
        self.assertNotIn('untracked.jks', str(result))


if __name__ == '__main__':
    unittest.main()
