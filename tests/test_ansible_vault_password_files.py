"""Recognize conventional Ansible Vault password files without exposing contents."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import classify


class AnsibleVaultPasswordFileTests(unittest.TestCase):
    def test_password_filenames_and_editor_backups(self):
        for path in (
            '.vault_pass', '.vault_password', '.vault_pass.txt', 'vault-password.txt',
            'deploy/.vault_pass', 'deploy/.vault_pass.bak', 'DEPLOY\\.VAULT_PASS',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential file')

    def test_templates_and_unrelated_vault_files_not_flagged(self):
        for path in (
            '.vault_pass.example', 'vault-password.txt.sample',
            'docs/vault-password.txt.template', 'vault.yml', 'vault-passwords.md',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_git_index_reports_staged_password_filename_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.vault_pass').write_text('SECRET_MUST_NOT_APPEAR', encoding='utf-8')
            (root / '.vault_pass.example').write_text('placeholder', encoding='utf-8')
            (root / 'vault-password.txt').write_text('UNTRACKED_SECRET', encoding='utf-8')
            subprocess.run(
                ['git', '-C', str(root), 'add', '.vault_pass', '.vault_pass.example'],
                check=True,
            )
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 2)
        self.assertEqual(report['candidates'], ['.vault_pass'])
        self.assertNotIn('SECRET_MUST_NOT_APPEAR', repr(report))
        self.assertNotIn('UNTRACKED_SECRET', repr(report))


if __name__ == '__main__':
    unittest.main()
