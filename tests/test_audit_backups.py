"""Ensure tracked backup copies of secrets are not missed by the filename audit."""

import unittest

from devpilot.audit import _potential_secret


class AuditBackupTests(unittest.TestCase):
    def test_credential_backup_names_are_detected(self):
        for name in (
            '.env.bak', 'config/.env.production.backup', 'id_ed25519.old',
            'certs/private.pem.orig', 'credentials.json.save',
            'secrets.tfvars.json~', 'terraform.tfstate.old',
            '.aws/credentials.bak', 'home/.config/gh/hosts.yml.old',
            'nested/.env.prod.bak.orig.old',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_template_backups_are_not_false_positives(self):
        for name in (
            '.env.example.bak', 'config/.env.production.template.old',
            'secrets.tfvars.json.example.orig', 'README.md.bak',
            'src/main.py.old',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    def test_env_template_name_with_live_suffix_remains_sensitive(self):
        self.assertTrue(_potential_secret('.env.example.local.bak'))


if __name__ == '__main__':
    unittest.main()
