"""Cloud storage client token/config files must be flagged in the basic index audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class StorageClientIndexAuditTests(unittest.TestCase):
    def test_credentials_and_nested_backup_copies_are_sensitive(self):
        for path in (
            '.s3cfg', 'home/.s3cfg', 'PROFILE\\.BOTO',
            'config/rclone/rclone.conf', 'RCLONE.CONF',
            'backups/rclone.conf.bak.old', '.s3cfg~', '.boto.swp',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_configs_are_not_flagged(self):
        for path in (
            '.s3cfg.example', '.boto.sample', 'rclone.conf.template',
            'rclone.conf.example.bak', 'rclone.conf.dist',
            'docs/rclone.md', 'config/storage.conf',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_storage_credentials_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            tracked = ('.s3cfg', '.boto', 'config/rclone/rclone.conf',
                       '.s3cfg.example', 'README.md')
            for name in (*tracked, 'untracked/rclone.conf'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('FAKE_SECRET_NOT_FOR_LOGGING', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *tracked], cwd=root, check=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 5)
        self.assertEqual(report['candidates'], [
            '.boto', '.s3cfg', 'config/rclone/rclone.conf',
        ])
        self.assertNotIn('FAKE_SECRET_NOT_FOR_LOGGING', str(report))
        self.assertNotIn('untracked/rclone.conf', str(report))


if __name__ == '__main__':
    unittest.main()
