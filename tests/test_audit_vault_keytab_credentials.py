"""Vault token and Kerberos keytab files must be flagged by both Git audits."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class VaultKeytabCredentialTests(unittest.TestCase):
    def test_sensitive_names_and_backups_are_detected(self):
        paths = (
            ".vault-token", "config/.vault-token",
            r"C:\Users\admin\.vault-token", "DEPLOY/.VAULT-TOKEN.BAK",
            "service.keytab", "secrets/HTTP.KEYTAB",
            "keys/prod.keytab.bak.old", "secrets/service.keytab.swp",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertIsNotNone(classify(path))

    def test_public_templates_and_unrelated_names_are_ignored(self):
        paths = (
            ".vault-token.example", ".vault-token.sample.old",
            "service.keytab.template", "service.keytab.sample.bak",
            "docs/keytab-guide.md", "src/vault-token.py",
            "config/.vault-token-placeholder",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_keytab_category_is_accurate(self):
        self.assertEqual(classify("identity.keytab"), "potential Kerberos credential file")

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_staged_files_are_reported_without_reading_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            staged = (
                "config/.vault-token", "auth/service.keytab",
                "auth/service.keytab.example", "docs/keytab-guide.md",
            )
            for relative in staged:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("SECRET_VALUE_NEVER_PRINT", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "--", *staged], check=True)

            regular = audit(root, redact_paths=True)
            legacy = audit_tracked_files(root)

        self.assertEqual(regular["tracked_files_checked"], 4)
        self.assertEqual(len(regular["findings"]), 2)
        self.assertTrue(all("path" not in item for item in regular["findings"]))
        self.assertEqual(legacy["candidates"], ["auth/service.keytab", "config/.vault-token"])
        self.assertNotIn("SECRET_VALUE_NEVER_PRINT", json.dumps(regular))
        self.assertNotIn("SECRET_VALUE_NEVER_PRINT", json.dumps(legacy))


if __name__ == "__main__":
    unittest.main()
