"""The lightweight Git audit must catch auth files recognized by secret_audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import classify


class AuthenticationFileParityTests(unittest.TestCase):
    def test_password_and_database_service_files_match_both_audits(self):
        for path in (
            '.htpasswd', 'site/.htpasswd', 'SITE/.HTPASSWD',
            '.pg_service.conf', 'database/.pg_service.conf',
            'site/.htpasswd.bak', 'database/.pg_service.conf.orig',
            'C:\\workspace\\.htpasswd',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential file')

    def test_templates_and_similarly_named_files_are_not_sensitive(self):
        for path in (
            '.htpasswd.example', '.htpasswd.sample',
            '.pg_service.conf.template', '.pg_service.conf.defaults',
            'docs/htpasswd.md', 'docs/pg_service.conf',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_audit_reports_sensitive_paths_not_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            entries = {
                '.htpasswd': 'PRIVATE_PASSWORD_HASH',
                '.pg_service.conf': 'password=PRIVATE_DATABASE_PASSWORD',
                '.htpasswd.example': 'example only',
            }
            for name, value in entries.items():
                (root / name).write_text(value, encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            report = audit_tracked_files(root)
            self.assertNotIn('error', report)
            self.assertEqual(report['tracked_files'], 3)
            self.assertEqual(report['candidates'], ['.htpasswd', '.pg_service.conf'])
            self.assertNotIn('PRIVATE_PASSWORD_HASH', repr(report))
            self.assertNotIn('PRIVATE_DATABASE_PASSWORD', repr(report))


if __name__ == '__main__':
    unittest.main()
