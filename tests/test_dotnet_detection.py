"""Regression tests for safe .NET project and test-command discovery."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import detect_projects, test_commands


class DotnetDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name):
        (self.root / name).write_text('', encoding='utf-8')

    def dotnet_commands(self):
        return [cmd for cmd in test_commands(self.root) if cmd['ecosystem'] == '.NET']

    def test_single_solution_preferred_over_multiple_projects(self):
        for name in ('Workspace.sln', 'App.csproj', 'Tests.csproj'):
            self.write(name)
        self.assertEqual(detect_projects(self.root), ['.NET'])
        self.assertEqual(self.dotnet_commands()[0]['argv'], ['dotnet', 'test', 'Workspace.sln'])

    def test_single_visual_basic_project(self):
        self.write('Service.vbproj')
        self.assertIn('.NET', detect_projects(self.root))
        self.assertEqual(self.dotnet_commands()[0]['argv'], ['dotnet', 'test', 'Service.vbproj'])

    def test_ambiguous_projects_do_not_guess(self):
        self.write('App.csproj')
        self.write('Tests.csproj')
        self.assertIn('.NET', detect_projects(self.root))
        self.assertEqual(self.dotnet_commands(), [])

    def test_ambiguous_solutions_do_not_guess(self):
        self.write('A.sln')
        self.write('B.slnx')
        self.assertEqual(self.dotnet_commands(), [])

    def test_symlinked_project_is_not_inspected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'Secret.csproj'
            target.write_text('', encoding='utf-8')
            try:
                (self.root / 'Secret.csproj').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this platform')
            self.assertNotIn('.NET', detect_projects(self.root))
            self.assertEqual(self.dotnet_commands(), [])


if __name__ == '__main__':
    unittest.main()
