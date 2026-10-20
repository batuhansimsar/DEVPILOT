"""Keep the standalone secret audit aligned with common credential locations."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret
from devpilot.secret_audit import audit, classify


SENSITIVE = (
    ".terraformrc",
    "configs/.terraformrc.bak",
    "private/auth.json",
    ".yarnrc",
    "frontend/.yarnrc.yml",
    "home/.pgpass",
    "db/.my.cnf",
    ".mylogin.cnf.backup",
    ".config/gcloud/credentials.db",
    ".config/gcloud/access_tokens.db",
    ".config/pypoetry/auth.toml",
    ".config/pip/pip.conf",
    "pip/pip.ini",
)


class CredentialParityTests(unittest.TestCase):
    def test_sensitive_auth_files_match_general_audit(self):
        for path in SENSITIVE:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertIsNotNone(classify(path))
                self.assertIsNotNone(classify(path.upper().replace("/", "\\")))

    def test_templates_and_unrelated_names_are_not_credentials(self):
        for path in (
            ".terraformrc.example", ".pgpass.sample", ".my.cnf.template",
            "auth.json.example", ".yarnrc.yml.dist",
            "docs/credentials.db", "docs/access_tokens.db",
            "docs/auth.toml", "docs/pip.conf", "docs/pip.ini",
            ".config/gcloud/credentials.db.example",
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which("git"), "Git is required for integration test")
    def test_staged_credentials_detected_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True,
                           stdout=subprocess.DEVNULL)
            paths = (".pgpass", ".config/pypoetry/auth.toml",
                     ".config/gcloud/credentials.db", "docs/credentials.db")
            for name in paths:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("do-not-print-this-token", encoding="utf-8")
            subprocess.run(["git", "add", "--", *paths], cwd=root, check=True,
                           stdout=subprocess.DEVNULL)
            report = audit(root, redact_paths=True)
        self.assertEqual(report["tracked_files_checked"], len(paths))
        self.assertEqual(len(report["findings"]), 3)
        self.assertTrue(all("path" not in item for item in report["findings"]))
        self.assertNotIn("do-not-print-this-token", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
