"""Sentry authentication filenames must be detected by both Git audits."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class SentryCredentialsParityTests(unittest.TestCase):
    def test_sentry_configs_and_editor_backups(self):
        paths = (
            '.sentryclirc',
            'app/.sentryclirc',
            'app/.sentryclirc.bak',
            r'APP\\.SENTRYCLIRC',
            'sentry.properties',
            'android/sentry.properties',
            'android/SENTRY.PROPERTIES.old',
            'android/.sentry.properties.swp',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential Sentry authentication configuration')

    def test_templates_and_unrelated_files_are_ignored(self):
        paths = (
            '.sentryclirc.example',
            'app/.sentryclirc.sample',
            'sentry.properties.template',
            'android/sentry.properties.dist.bak',
            'docs/sentry.properties.md',
            'docs/sentry-cli.md',
            'README.md',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_index_only_scan_matches_detailed_audit_and_never_reads_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            sensitive = ('.sentryclirc', 'android/sentry.properties')
            safe = ('.sentryclirc.example', 'android/sentry.properties.template', 'README.md')
            for name in (*sensitive, *safe, 'untracked/.sentryclirc'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *sensitive, *safe],
                           cwd=root, check=True, capture_output=True)
            simple = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)

        self.assertNotIn('error', simple)
        self.assertEqual(simple['tracked_files'], len(sensitive) + len(safe))
        self.assertEqual(simple['candidates'], sorted(sensitive))
        self.assertEqual(detailed['tracked_files_checked'], len(sensitive) + len(safe))
        self.assertEqual(len(detailed['findings']), len(sensitive))
        self.assertTrue(all(item['category'] == 'potential Sentry authentication configuration'
                            and 'path' not in item for item in detailed['findings']))
        self.assertNotIn('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', repr(simple))
        self.assertNotIn('PRIVATE_TEST_TOKEN_DO_NOT_PRINT', repr(detailed))
        self.assertNotIn('untracked', repr(simple))


if __name__ == '__main__':
    unittest.main()
