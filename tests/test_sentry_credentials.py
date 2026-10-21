"""Regression tests for filename-only Sentry credentials auditing."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.sentry_credentials import is_sentry_auth_config
from devpilot.secret_audit import audit, classify
from devpilot.audit import _potential_secret, audit_tracked_files


class SentryCredentialTests(unittest.TestCase):
    def test_conventional_auth_filenames(self):
        for path in ('.sentryclirc', 'backend/.sentryclirc',
                     'backend/sentry.properties', 'SENTRY.PROPERTIES',
                     r'backend\.SENTRYCLIRC', 'config/.sentryclirc.bak'):
            with self.subTest(path=path):
                self.assertEqual(classify(path),
                                 'potential Sentry authentication configuration')

    def test_template_and_unrelated_paths(self):
        for path in ('sentry.properties.example', '.sentryclirc.sample',
                     'sentry.properties.template', 'docs/sentry.md',
                     'src/sentry.properties.md', 'project/sentry.json'):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    def test_cli_audit_agrees_with_sentry_secret_classification(self):
        for path in ('.sentryclirc', 'backend/.sentryclirc',
                     'backend/sentry.properties', r'config\\SENTRY.PROPERTIES',
                     '.sentryclirc.bak', 'sentry.properties.old'):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertIsNotNone(classify(path))
        for path in ('sentry.properties.example', '.sentryclirc.sample',
                     'docs/sentry.md', 'config/settings.properties'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_cli_audit_flags_tracked_sentry_auth_without_reading_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            path = root / 'config' / '.sentryclirc'
            path.parent.mkdir()
            path.write_text('auth.token=never_print_this_secret')
            (root / 'sentry.properties').write_text('auth.token=another_secret')
            subprocess.run(['git', 'add', '--', 'config/.sentryclirc',
                            'sentry.properties'], cwd=root, check=True)
            report = audit_tracked_files(root)
            self.assertEqual(report['candidates'], ['config/.sentryclirc',
                                                    'sentry.properties'])
            self.assertEqual(report['tracked_files'], 2)
            self.assertNotIn('never_print_this_secret', str(report))
            self.assertNotIn('another_secret', str(report))

    def test_helper_rejects_other_configuration(self):
        self.assertTrue(is_sentry_auth_config(('config', '.sentryclirc')))
        self.assertTrue(is_sentry_auth_config(('sentry.properties',)))
        self.assertFalse(is_sentry_auth_config(()))
        self.assertFalse(is_sentry_auth_config(('config', 'settings.properties')))

    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_tracked_tokens_are_never_read_or_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            secrets = root / 'config' / '.sentryclirc'
            secrets.parent.mkdir()
            secrets.write_text('auth.token=must_not_appear_in_report')
            (root / 'sentry.properties').write_text('auth.token=another_private_token')
            subprocess.run(['git', 'add', '--', 'config/.sentryclirc',
                            'sentry.properties'], cwd=root, check=True)
            report = audit(root, redact_paths=True)
            self.assertFalse(report['ok'])
            self.assertEqual(len(report['findings']), 2)
            serialized = json.dumps(report)
            self.assertNotIn('must_not_appear_in_report', serialized)
            self.assertNotIn('another_private_token', serialized)
            self.assertTrue(all('path' not in item for item in report['findings']))


if __name__ == '__main__':
    unittest.main()
