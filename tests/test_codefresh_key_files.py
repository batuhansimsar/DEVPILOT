"""Codefresh's root pipeline should appear in Python repository analysis."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class CodefreshKeyFilesTests(unittest.TestCase):
    def test_root_pipeline_is_reported_without_nested_or_backup_lookalikes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "codefresh.yml").write_text("version: '1.0'\n", encoding="utf-8")
            (root / "codefresh.yml.bak").write_text("backup", encoding="utf-8")
            nested = root / "services"
            nested.mkdir()
            (nested / "codefresh.yml").write_text("nested", encoding="utf-8")
            report = analyze_project(root)
        self.assertIn("codefresh.yml", report["key_files"])
        self.assertNotIn("codefresh.yml.bak", report["key_files"])
        self.assertNotIn("services/codefresh.yml", report["key_files"])


if __name__ == "__main__":
    unittest.main()
