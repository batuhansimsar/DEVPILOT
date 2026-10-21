"""Cloud CLI credential filename audits must be consistent and read-only."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.cloud_cli_credentials import is_cloud_cli_credential_location
from devpilot.secret_audit import audit, classify


class CloudCLICredentialTests(unittest.TestCase):
    def test_exact_auth_config_locations_in_both_audits(self):
        sensitive = (
            '.config/doctl/config.yaml',
            'home/doctl/config.yaml',
            'AppData\\Local\\doctl\\config\\config.yaml',
            'Library/Application Support/doctl/config.yaml',
            '.config/stripe/config.toml',
            'home/.config/stripe/config.toml.bak',
        )
        for path in sensitive:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential cloud CLI credential configuration')

    def test_unrelated_configs_and_templates_are_not_flagged(self):
        safe = (
            'docs/config.toml',
            'src/stripe/config.toml',
            '.config/stripe/config.json',
            '.config/doctl/config.toml',
            'doctl/config.yml',
            'doctl/config.yaml.example',
            '.config/stripe/config.toml.template',
            '.config/doctl/config.yaml.sample.bak',
        )
        for path in safe:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_helper_does_not_match_unrelated_suffixes(self):
        self.assertTrue(is_cloud_cli_credential_location(('.config', 'stripe', 'config.toml')))
        self.assertFalse(is_cloud_cli_credential_location(('docs', 'stripe', 'config.toml')))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_tracked_credentials_are_reported_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            sensitive = ('.config/doctl/config.yaml', '.config/stripe/config.toml')
            safe = ('.config/doctl/config.yaml.example', 'src/stripe/config.toml')
            for name in (*sensitive, *safe, 'untracked/doctl/config.yaml'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *sensitive, *safe],
                           cwd=root, check=True, capture_output=True)
            quick = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)
        self.assertNotIn('error', quick)
        self.assertEqual(quick['candidates'], list(sensitive))
        self.assertEqual(quick['tracked_files'], 4)
        self.assertEqual(detailed['tracked_files_checked'], 4)
        self.assertEqual(len(detailed['findings']), 2)
        self.assertTrue(all(item['category'] == 'potential cloud CLI credential configuration'
                            and 'path' not in item for item in detailed['findings']))
        self.assertNotIn('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', repr(quick))
        self.assertNotIn('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', repr(detailed))
        self.assertNotIn('untracked', repr(quick))


if __name__ == '__main__':
    unittest.main()
