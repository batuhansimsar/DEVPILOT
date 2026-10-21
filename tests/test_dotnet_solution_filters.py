"""Solution filters are .NET markers and safe, explicit test targets."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dotnet_manifests import dotnet_test_target, is_dotnet_manifest
from devpilot.core import analyze_project, detect_projects, test_commands
from devpilot.workspaces import discover_workspaces


class DotnetSolutionFilterTests(unittest.TestCase):
    def test_recognizes_solution_filter_but_not_backups(self):
        self.assertTrue(is_dotnet_manifest('Backend.SLNF'))
        self.assertTrue(is_dotnet_manifest('Backend.slnf'))
        self.assertFalse(is_dotnet_manifest('Backend.slnf.bak'))
        self.assertFalse(is_dotnet_manifest('Backend.slnff'))

    def test_only_solution_filter_is_valid_test_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Backend.slnf').write_text('{"solution": {"path": "Backend.sln"}}')
            self.assertIn('.NET', detect_projects(root))
            self.assertIn('Backend.slnf', analyze_project(root)['key_files'])
            self.assertEqual(
                [item['argv'] for item in test_commands(root) if item['ecosystem'] == '.NET'],
                [['dotnet', 'test', 'Backend.slnf']],
            )

    def test_full_solution_preferred_over_optional_filters(self):
        self.assertEqual(dotnet_test_target({'Backend.sln', 'Backend.slnf'}), 'Backend.sln')
        self.assertIsNone(dotnet_test_target({'A.slnf', 'B.slnf'}))
        self.assertIsNone(dotnet_test_target({'A.sln', 'B.slnx', 'C.slnf'}))
        self.assertEqual(dotnet_test_target({'Backend.slnf', 'Api.csproj'}), 'Backend.slnf')

    def test_nested_solution_filter_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / 'api'
            child.mkdir()
            (child / 'Api.slnf').write_text('{}')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'api')
            self.assertEqual(report['workspaces'][0]['manifests'],
                             [{'file': 'Api.slnf', 'ecosystem': '.NET'}])

    def test_symlinked_solution_filter_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'Outside.slnf'
            target.write_text('{}')
            try:
                (root / 'Outside.slnf').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('.NET', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
