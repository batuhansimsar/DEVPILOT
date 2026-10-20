"""Regression coverage for credential-bearing authentication config paths."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class AuthenticationConfigFilenameTests(unittest.TestCase):
    def test_password_and_database_service_files_are_sensitive(self):
        for path in (
            '.htpasswd', 'site/.htpasswd', 'SITE/.HTPASSWD',
            '.pg_service.conf', 'database/.pg_service.conf',
            'site/.htpasswd.bak', 'database/.pg_service.conf.orig',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential file')

    def test_safe_templates_and_similar_filenames_remain_unflagged(self):
        for path in (
            '.htpasswd.example', '.htpasswd.sample',
            '.pg_service.conf.template', '.pg_service.conf.defaults',
            'docs/htpasswd.md', 'docs/pg_service.conf',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_index_audit_flags_only_sensitive_paths_without_reading_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for name, content in (
                ('.htpasswd', 'SECRET_PASSWORD_HASH'),
                ('.pg_service.conf', 'password=PRIVATE_DATABASE_PASSWORD'),
                ('.htpasswd.example', 'public sample'),
            ):
                (root / name).write_text(content, encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            report = audit(root, redact_paths=True)
            self.assertFalse(report['ok'])
            self.assertEqual(report['tracked_files_checked'], 3)
            self.assertEqual(len(report['findings']), 2)
            self.assertTrue(all('path' not in item for item in report['findings']))
            serialized = json.dumps(report)
            self.assertNotIn('SECRET_PASSWORD_HASH', serialized)
            self.assertNotIn('PRIVATE_DATABASE_PASSWORD', serialized)


if __name__ == '__main__':
    unittest.main()
