"""Regression tests for private-key formats used by Apple and PuTTY tooling."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class PrivateKeyFormatAuditTests(unittest.TestCase):
    def test_private_key_filenames_and_backups_are_flagged(self):
        for path in (
            'keys/AuthKey_TEST123.p8', 'keys/PUTTY_KEY.ppk',
            'keys/signing.P8.bak', 'keys/login.PPK.old.orig',
            'keys/service.JCEKS', 'keys/android.BKS.bak',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential private key or certificate')

    def test_templates_and_unrelated_files_are_not_flagged(self):
        for path in (
            'keys/AuthKey_TEST123.p8.example',
            'keys/login.ppk.sample',
            'keys/service.jceks.example', 'keys/android.bks.sample',
            'docs/key-formats.md',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git required for index audit')
    def test_only_tracked_private_keys_are_reported_without_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for filename in ('AuthKey_TEST.p8', 'deploy.ppk', 'server.jceks',
                             'wallet.bks', 'deploy.ppk.sample', 'untracked.p8'):
                (root / filename).write_text('SYNTHETIC-FIXTURE-DO-NOT-PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', 'AuthKey_TEST.p8',
                            'deploy.ppk', 'server.jceks', 'wallet.bks',
                            'deploy.ppk.sample'], cwd=root, check=True)
            regular_report = audit_tracked_files(root)
            detailed_report = audit(root)

        self.assertEqual(regular_report['tracked_files'], 5)
        self.assertEqual(regular_report['candidates'],
                         ['AuthKey_TEST.p8', 'deploy.ppk', 'server.jceks', 'wallet.bks'])
        self.assertEqual(detailed_report['tracked_files_checked'], 5)
        self.assertEqual(
            [item['path'] for item in detailed_report['findings']],
            ['AuthKey_TEST.p8', 'deploy.ppk', 'server.jceks', 'wallet.bks'],
        )
        self.assertNotIn('SYNTHETIC-FIXTURE-DO-NOT-PRINT', str(regular_report))
        self.assertNotIn('SYNTHETIC-FIXTURE-DO-NOT-PRINT', str(detailed_report))


if __name__ == '__main__':
    unittest.main()
