"""Independent secret audit must detect credential paths covered by CLI audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class SecretAuditCredentialParityTests(unittest.TestCase):
    def test_database_and_package_manager_credentials(self):
        paths = (
            '.pgpass', 'db/.my.cnf', '.mylogin.cnf',
            '.terraformrc', 'infra/credentials.tfrc.json',
            'registry/auth.json', '.yarnrc', 'project/.yarnrc.yml',
            'home/.config/pypoetry/auth.toml',
            'home/.config/pip/pip.conf', 'C:\\Users\\me\\pip\\pip.ini',
            'backups/.pgpass.bak.tmp', 'backup/.mylogin.cnf.swp',
            'backup/.npmrc.swo',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))

    def test_templates_and_unrelated_files_are_ignored(self):
        paths = (
            '.pgpass.example', '.my.cnf.template', '.yarnrc.yml.sample',
            'registry/auth.json.dist', '.terraformrc.example',
            '.config/pip/pip.conf.sample', 'src/auth.toml',
            'docs/pip.conf', 'docs/.my.cnf.example.bak',
            'src/settings.json',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_staged_credentials_without_exposing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            staged = ('.pgpass', '.my.cnf', '.yarnrc.yml',
                      '.config/pypoetry/auth.toml', 'docs/pip.conf',
                      '.pgpass.example')
            for relative in (*staged, 'untracked/.mylogin.cnf'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PRIVATE_TOKEN_NEVER_PRINT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *staged], check=True)
            report = audit(root, redact_paths=True)
            self.assertEqual(report['tracked_files_checked'], len(staged))
            self.assertEqual(len(report['findings']), 4)
            self.assertTrue(all('path' not in item for item in report['findings']))
            self.assertNotIn('PRIVATE_TOKEN_NEVER_PRINT', str(report))
            self.assertNotIn('untracked', str(report))


if __name__ == '__main__':
    unittest.main()
