"""Regression coverage for private age identities tracked under conventional config paths."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class AgeIdentityAuditTests(unittest.TestCase):
    def test_detects_age_identity_paths_and_backups_in_both_audits(self):
        sensitive = (
            '.config/sops/age/keys.txt',
            'home/.config/sops/age/keys.txt',
            'home/.config/age/keys.txt',
            r'C:\Users\me\.config\sops\age\keys.txt',
            '.config/sops/age/keys.txt.bak',
            '.config/sops/age/keys.txt.swo',
            '.config/sops/age/.keys.txt.swp',
        )
        for path in sensitive:
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential age private identity')
                self.assertTrue(_potential_secret(path))

    def test_does_not_classify_generic_key_lists_or_templates(self):
        harmless = (
            'docs/keys.txt',
            'docs/sops/age/keys.txt',
            '.config/sops/keys.txt',
            '.config/sops/age/keys.txt.example',
            '.config/sops/age/keys.txt.sample.bak',
            '.config/age/keys.txt.template',
            '.config/sops/age/README.md',
        )
        for path in harmless:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_staged_age_identity_is_reported_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            sensitive = ('.config/sops/age/keys.txt', '.config/age/keys.txt')
            safe = ('docs/keys.txt', '.config/sops/age/keys.txt.sample')
            for name in (*sensitive, *safe, 'untracked/keys.txt'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('AGE-SECRET-KEY-DO-NOT-PRINT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *sensitive, *safe], check=True)
            report = audit(root, redact_paths=True)
            cli_report = audit_tracked_files(root)
            self.assertEqual(report['tracked_files_checked'], 4)
            self.assertEqual(len(report['findings']), 2)
            self.assertTrue(all(item['category'] == 'potential age private identity'
                                and 'path' not in item for item in report['findings']))
            self.assertEqual(cli_report['candidates'], sorted(sensitive))
            self.assertEqual(cli_report['tracked_files'], 4)
            self.assertNotIn('AGE-SECRET-KEY-DO-NOT-PRINT', json.dumps(report))
            self.assertNotIn('AGE-SECRET-KEY-DO-NOT-PRINT', json.dumps(cli_report))


if __name__ == '__main__':
    unittest.main()
