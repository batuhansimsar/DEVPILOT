"""Helm's saved chart repository and OCI registry credentials need auditing."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class HelmCredentialAuditTests(unittest.TestCase):
    def test_helm_config_files_and_editor_backups_are_sensitive(self):
        for path in (
            "home/.config/helm/repositories.yaml",
            "home/.config/helm/registry/config.json",
            "home/.config/helm/repositories.yaml.bak",
            "home/.config/helm/registry/config.json.~3~",
            "HOME\\.config\\HELM\\repositories.yaml",
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), "potential credential configuration")
                self.assertTrue(_potential_secret(path))

    def test_generic_chart_files_and_templates_are_not_flagged(self):
        for path in (
            "charts/repositories.yaml",
            "charts/values.yaml",
            "helm/repositories.yaml",
            ".config/helm/repositories.yaml.example",
            ".config/helm/registry/config.example.json",
            ".config/docker/readme.json",
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_index_scan_reports_helm_credentials_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            paths = (
                ".config/helm/repositories.yaml",
                ".config/helm/registry/config.json",
                "charts/repositories.yaml",
            )
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("DO_NOT_REVEAL_THIS_PASSWORD", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "--", *paths], check=True)
            standalone = audit(root, redact_paths=True)
            cli = audit_tracked_files(root)

        self.assertEqual(standalone["tracked_files_checked"], len(paths))
        self.assertEqual(len(standalone["findings"]), 2)
        self.assertTrue(all("path" not in item for item in standalone["findings"]))
        self.assertEqual(cli["candidates"], sorted(paths[:2]))
        self.assertNotIn("DO_NOT_REVEAL_THIS_PASSWORD", str(standalone) + str(cli))


if __name__ == "__main__":
    unittest.main()
