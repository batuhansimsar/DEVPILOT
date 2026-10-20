"""Check that the audit detects OpenSSH hardware-backed credential filenames."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class SshSecurityKeyAuditTests(unittest.TestCase):
    def test_security_key_files_and_backups_are_sensitive(self):
        for path in (
            'id_ed25519_sk', 'id_ecdsa_sk',
            'keys/id_ed25519_sk.bak', 'keys/id_ecdsa_sk.old',
            'KEYS/ID_ED25519_SK',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_public_keys_and_non_secret_files_remain_safe(self):
        for path in ('id_ed25519_sk.pub', 'id_ecdsa_sk.pub', 'docs/keys.md'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    def test_git_index_reports_only_tracked_private_key_filenames(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for filename in ('id_ed25519_sk', 'id_ed25519_sk.pub', 'id_ecdsa_sk'):
                (root / filename).write_text('TEST ONLY', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', 'id_ed25519_sk', 'id_ed25519_sk.pub'], check=True)
            report = audit_tracked_files(root)
        self.assertEqual(report['tracked_files'], 2)
        self.assertEqual(report['candidates'], ['id_ed25519_sk'])
        self.assertNotIn('error', report)


if __name__ == '__main__':
    unittest.main()
