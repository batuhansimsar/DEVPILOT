"""Temporary/editor backups of credential files must be audited, not ignored."""
import unittest
from devpilot.audit import _potential_secret


class AuditTemporaryBackupTests(unittest.TestCase):
    def test_sensitive_temporary_and_editor_copies(self):
        for path in (
            'tls/private.pem.tmp', 'keys/id_ed25519.swp',
            '.ssh/id_rsa.swo', '.aws/credentials.tmp',
            'config/secrets.json.swp', 'credentials.tfrc.json.swo',
            'nested/private.key.tmp.old',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_templates_and_nonsensitive_temp_files(self):
        for path in (
            '.env.example.tmp', '.env.production.sample.swp',
            'secrets.tfvars.json.example.swo',
            'README.md.tmp', 'src/main.py.swp',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    def test_active_env_temp_file_remains_sensitive(self):
        self.assertTrue(_potential_secret('.env.production.tmp'))


if __name__ == '__main__':
    unittest.main()
