"""Both tracked-filename auditors detect Cargo registry authentication stores."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class CargoCredentialsAuditTests(unittest.TestCase):
    def test_current_legacy_and_backup_copies_detected_by_both_auditors(self):
        for path in (
            '.cargo/credentials.toml',
            'project/.cargo/credentials',
            r'HOME\.CARGO\CREDENTIALS.TOML',
            '.cargo/credentials.toml.bak',
            'project/.cargo/credentials.swp',
            'project/.cargo/credentials.toml.~3~',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential Cargo registry credentials')

    def test_unrelated_files_and_templates_stay_unflagged(self):
        for path in (
            'docs/credentials.toml',
            'src/config.toml',
            '.cargo/config.toml',
            '.cargo/credentials.toml.example',
            '.cargo/credentials.sample',
            '.cargo/credentials.toml.example.bak',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_index_reports_only_tracked_cargo_credentials_without_reading_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            tracked = (
                '.cargo/credentials.toml',
                'legacy/.cargo/credentials',
                '.cargo/config.toml',
                '.cargo/credentials.toml.example',
            )
            for name in (*tracked, 'untracked/.cargo/credentials.toml'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('PRIVATE_CARGO_TOKEN_NEVER_LOG', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *tracked], check=True)
            basic = audit_tracked_files(root)
            redacted = audit(root, redact_paths=True)
        self.assertEqual(basic['candidates'], ['.cargo/credentials.toml', 'legacy/.cargo/credentials'])
        self.assertEqual(len(redacted['findings']), 2)
        self.assertTrue(all('path' not in finding for finding in redacted['findings']))
        self.assertNotIn('PRIVATE_CARGO_TOKEN_NEVER_LOG', str(basic) + str(redacted))


if __name__ == '__main__':
    unittest.main()
