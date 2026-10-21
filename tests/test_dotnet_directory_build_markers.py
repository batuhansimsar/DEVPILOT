"""MSBuild Directory.Build convention files count as .NET project markers."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project, detect_projects, test_commands
from devpilot.dotnet_manifests import dotnet_test_target, is_dotnet_manifest
from devpilot.workspaces import discover_workspaces


class DirectoryBuildMarkersTests(unittest.TestCase):
    def test_msbuild_convention_files_are_discoverable_but_not_test_targets(self):
        for filename in ('Directory.Build.props', 'Directory.Build.targets'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / filename).write_text('<Project />', encoding='utf-8')
                self.assertTrue(is_dotnet_manifest(filename))
                self.assertIn('.NET', detect_projects(root))
                self.assertIn(filename, analyze_project(root)['key_files'])
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['manifests'],
                                 [{'file': filename, 'ecosystem': '.NET'}])
                self.assertIsNone(dotnet_test_target({filename}))
                self.assertFalse(any(command['ecosystem'] == '.NET'
                                     for command in test_commands(root)))

    def test_suffixes_and_links_are_not_treated_as_project_markers(self):
        for filename in ('Directory.Build.props.bak', 'Directory.Build.targets.old',
                         'directory.build.props', 'Directory.Build.target'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / filename).touch()
                self.assertNotIn('.NET', detect_projects(root))
                self.assertFalse(is_dotnet_manifest(filename))
                self.assertEqual(discover_workspaces(root)['workspace_count'], 0)
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            target = Path(outside) / 'Directory.Build.props'
            target.touch()
            try:
                (root / 'Directory.Build.props').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('.NET', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
