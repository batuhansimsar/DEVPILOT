"""NuGet config and lockfile-only projects must be identified consistently."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project, detect_projects
from devpilot.dotnet_manifests import is_dotnet_manifest
from devpilot.workspaces import discover_workspaces


class DotnetNugetMarkerTests(unittest.TestCase):
    def test_root_markers_agree_across_project_and_workspace_analysis(self):
        for name in ("NuGet.Config", "nuget.config", "packages.lock.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / name).write_text("", encoding="utf-8")

                self.assertTrue(is_dotnet_manifest(name))
                self.assertIn(".NET", detect_projects(root))
                self.assertIn(name, analyze_project(root)["key_files"])
                workspaces = discover_workspaces(root)
                self.assertEqual(workspaces["workspace_count"], 1)
                self.assertEqual(workspaces["workspaces"][0]["manifests"],
                                 [{"file": name, "ecosystem": ".NET"}])

    def test_nested_nuget_lockfile_is_discovered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            nested = root / "services" / "backend"
            nested.mkdir(parents=True)
            (nested / "packages.lock.json").write_text("{}", encoding="utf-8")
            report = discover_workspaces(root)
            self.assertEqual(report["workspace_count"], 1)
            self.assertEqual(report["workspaces"][0]["path"], "services/backend")
            self.assertEqual(report["workspaces"][0]["ecosystems"], [".NET"])

    def test_backups_and_symlinked_markers_do_not_trigger_detection(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as external:
            root = Path(folder)
            for name in ("NuGet.Config.bak", "packages.lock.json.bak", "NuGet.CONFIG"):
                (root / name).write_text("", encoding="utf-8")
                self.assertFalse(is_dotnet_manifest(name))

            outside = Path(external) / "NuGet.Config"
            outside.write_text("secret", encoding="utf-8")
            try:
                (root / "NuGet.Config").symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertNotIn(".NET", detect_projects(root))
            self.assertEqual(discover_workspaces(root)["workspace_count"], 0)


if __name__ == "__main__":
    unittest.main()
