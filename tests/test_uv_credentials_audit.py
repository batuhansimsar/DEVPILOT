"""Regression coverage for credential-bearing uv user configuration paths."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class UvCredentialAuditTests(unittest.TestCase):
    def test_uv_user_configs_are_flagged(self):
        for path in (
            ".config/uv/uv.toml",
            "uv/uv.toml",
            "home/.config/uv/uv.toml",
            "uv\\uv.toml.bak",
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_unrelated_project_files_are_not_flagged(self):
        for path in ("uv.lock", "pyproject.toml", "src/uv.toml", "uv.toml"):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which("git"), "Git not installed")
    def test_tracked_uv_config_does_not_expose_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            config = root / ".config" / "uv"
            config.mkdir(parents=True)
            (config / "uv.toml").write_text(
                'index-url = "https://user:dummy-private-token@example.invalid/simple"\n'
            )
            (root / "uv.lock").write_text("version = 1\n")
            subprocess.run(
                ["git", "-C", str(root), "add", ".config/uv/uv.toml", "uv.lock"],
                check=True, capture_output=True,
            )
            report = audit_tracked_files(root)
            self.assertEqual(report["tracked_files"], 2)
            self.assertEqual(report["candidates"], [".config/uv/uv.toml"])
            self.assertNotIn("dummy-private-token", str(report))


if __name__ == "__main__":
    unittest.main()
