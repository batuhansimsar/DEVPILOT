"""Prevent database client credential files from leaking into tracked source."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class DatabaseCredentialAuditTests(unittest.TestCase):
    def test_database_client_auth_files_and_backups_are_sensitive(self):
        for path in ('.pgpass', 'home/.pgpass', 'HOME\\.PGPASS',
                     'db/.my.cnf', '.mylogin.cnf', '.my.cnf.bak',
                     'credentials/.pgpass.orig', 'db/.mylogin.cnf.backup'):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_config_files_are_not_sensitive(self):
        for path in ('.pgpass.example', '.my.cnf.template', '.mylogin.cnf.sample',
                     'docs/postgres.md', 'src/my.cnf', 'src/pgpass.py'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_tracked_db_credentials_report_only_names_not_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('.pgpass', '.my.cnf', '.mylogin.cnf',
                         '.pgpass.example', 'untracked/.pgpass'):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('fixture-password-must-not-appear', encoding='utf-8')
            subprocess.run(['git', 'add', '--', '.pgpass', '.my.cnf',
                            '.mylogin.cnf', '.pgpass.example'], cwd=root, check=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 4)
        self.assertEqual(report['candidates'], ['.my.cnf', '.mylogin.cnf', '.pgpass'])
        self.assertNotIn('fixture-password-must-not-appear', str(report))
        self.assertNotIn('untracked/.pgpass', str(report))


if __name__ == '__main__':
    unittest.main()
