"""Emacs auto-save, lock, and numbered backup files must be audited."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class EmacsBackupsTests(unittest.TestCase):
    def test_sensitive_editor_copies_in_both_auditors(self):
        sensitive = (
            'credentials.json.~1~',
            'secrets.json.~27~.bak',
            '#id_ed25519#',
            '.#.npmrc',
            '#private.pem#.~42~',
            'nested/.env.production.~3~',
            'vars/#prod.tfvars#',
            '.aws/credentials.~5~',
            'home/.config/gh/#hosts.yml#',
        )
        for path in sensitive:
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_editor_files_remain_safe(self):
        safe = (
            'credentials.example.json.~1~',
            '#.env.example#',
            '.#.env.template',
            '#README.md#',
            'src/notes.txt.~19~',
            'vars/production.tfvars.json.example.~8~',
        )
        for path in safe:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    def test_nested_wrappers_and_vim_swap_are_supported(self):
        for path in ('#.env.production#.~12~.old', '.credentials.json.swp.~2~',
                     'credentials.json' + '.bak' * 40):
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_index_audits_editor_copies_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            filenames = ('credentials.json.~1~', '#id_ed25519#', '.#.npmrc',
                         'README.md.~2~', 'credentials.example.json.~2~')
            for filename in filenames:
                (root / filename).write_text('PRIVATE_CONTENT_NOT_FOR_REPORT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            redacted = audit(root, redact_paths=True)
            self.assertEqual(redacted['tracked_files_checked'], len(filenames))
            self.assertEqual(len(redacted['findings']), 3)
            self.assertNotIn('PRIVATE_CONTENT_NOT_FOR_REPORT', str(redacted))
            self.assertTrue(all('path' not in entry for entry in redacted['findings']))
            self.assertEqual(
                set(audit_tracked_files(root)['candidates']),
                set(filenames[:3]),
            )


if __name__ == '__main__':
    unittest.main()
