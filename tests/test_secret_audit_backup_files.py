"""Regression coverage for tracked credential backup filenames."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class BackupClassificationTests(unittest.TestCase):
    def test_sensitive_backups_are_detected(self):
        paths = (
            'credentials.json.backup',
            'nested/PRIVATE.KEY.BAK',
            'id_ed25519.old',
            '.aws/credentials.orig',
            'profiles/.config/gh/hosts.yml.save',
            'settings/.npmrc~',
            'infra/prod.tfstate.bak',
            'vars/production.tfvars.json.backup',
            'private.pem.backup.bak',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))

    def test_safe_files_and_templates_stay_excluded(self):
        paths = (
            'credentials.example.json.bak',
            'docs/.env.example.backup',
            'vars/production.tfvars.template.bak',
            'README.md.bak',
            'src/config.json.backup',
            'public.key.pub.bak',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_index_reports_backups_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for name, secret in (
                ('credentials.json.backup', 'SHOULD_NEVER_APPEAR_IN_OUTPUT'),
                ('prod.tfstate.bak', 'ALSO_PRIVATE'),
                ('credentials.example.json.bak', 'harmless example'),
            ):
                (root / name).write_text(secret, encoding='utf-8')
            subprocess.run(
                ['git', '-C', str(root), 'add', '--', '.'], check=True
            )
            report = audit(root, redact_paths=True)
            self.assertEqual(report['tracked_files_checked'], 3)
            self.assertEqual(len(report['findings']), 2)
            self.assertTrue(all('path' not in item for item in report['findings']))
            self.assertNotIn('SHOULD_NEVER_APPEAR_IN_OUTPUT', str(report))
            self.assertNotIn('ALSO_PRIVATE', str(report))


if __name__ == '__main__':
    unittest.main()
