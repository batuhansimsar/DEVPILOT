"""JetBrains safe-write copies of credentials remain visible to both audits."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.editor_backups import strip_editor_backups
from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import classify, audit


class JetBrainsSafeWriteTests(unittest.TestCase):
    def test_nested_jetbrains_suffixes_unwrap_without_losing_vim_flag(self):
        suffixes = ('.bak', '.swp')
        cases = {
            '.env.production.___jb_tmp___': ('.env.production', False),
            'credentials.json.___jb_old___': ('credentials.json', False),
            '.credentials.json.swp.___jb_tmp___': ('.credentials.json', True),
            '#id_ed25519#.___jb_old___.bak': ('id_ed25519', False),
            'secrets.json.___jb_tmp___.___jb_old___': ('secrets.json', False),
            '.___jb_tmp___': ('.___jb_tmp___', False),
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(strip_editor_backups(name, suffixes), expected)

    def test_both_auditors_find_sensitive_safe_write_copies(self):
        for path in (
            '.env.production.___jb_tmp___',
            'credentials.json.___jb_old___',
            '.aws/credentials.___jb_tmp___',
            'nested/.credentials.json.swp.___jb_old___',
            '#id_ed25519#.___jb_old___.bak',
        ):
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_safe_write_copies_are_not_findings(self):
        for path in (
            '.env.example.___jb_tmp___',
            'credentials.example.json.___jb_old___',
            'secrets.tfvars.json.example.___jb_tmp___',
            'README.md.___jb_old___',
            'src/main.py.___jb_tmp___',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_index_reports_jetbrains_copies_without_reading_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            filenames = (
                'credentials.json.___jb_tmp___',
                '.env.production.___jb_old___',
                'README.md.___jb_tmp___',
                'credentials.example.json.___jb_old___',
            )
            for name in filenames:
                (root / name).write_text('PRIVATE_DO_NOT_ECHO', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            flagged = audit(root, redact_paths=True)
            self.assertEqual(flagged['tracked_files_checked'], 4)
            self.assertEqual(len(flagged['findings']), 2)
            self.assertTrue(all('path' not in finding for finding in flagged['findings']))
            self.assertNotIn('PRIVATE_DO_NOT_ECHO', repr(flagged))
            self.assertEqual(set(audit_tracked_files(root)['candidates']), set(filenames[:2]))


if __name__ == '__main__':
    unittest.main()
