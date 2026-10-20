import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class WorkspaceDiscoveryTests(unittest.TestCase):
    def test_root_and_nested_projects(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'package.json').write_text('{}')
            (root / 'packages' / 'web').mkdir(parents=True)
            (root / 'packages' / 'web' / 'package.json').write_text('{}')
            (root / 'services' / 'api').mkdir(parents=True)
            (root / 'services' / 'api' / 'go.mod').write_text('module api')
            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 3)
            self.assertEqual([w['path'] for w in result['workspaces']], ['.', 'packages/web', 'services/api'])

    def test_multiple_manifests_in_one_directory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pyproject.toml').write_text('[project]')
            (root / 'requirements.txt').write_text('pytest')
            (root / 'backend.csproj').write_text('<Project />')
            workspace = discover_workspaces(root)['workspaces'][0]
            self.assertEqual(workspace['ecosystems'], ['.NET', 'Python'])
            self.assertEqual(len(workspace['manifests']), 3)

    def test_skips_dependency_directories(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'package.json').write_text('{}')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_and_directory_limits(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a' / 'b').mkdir(parents=True)
            (root / 'a' / 'b' / 'go.mod').write_text('module deep')
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 0)
            self.assertTrue(discover_workspaces(root, max_directories=1)['truncated'])

    def test_symlink_does_not_escape(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as external:
            root = Path(temp)
            (Path(external) / 'Cargo.toml').write_text('[package]')
            try:
                (root / 'external').symlink_to(external, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_invalid_limits(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                discover_workspaces(Path(temp), max_depth=-1)
            with self.assertRaises(ValueError):
                discover_workspaces(Path(temp), max_directories=0)


    def test_pipfile_nested_python_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / 'apps' / 'worker'
            nested.mkdir(parents=True)
            (nested / 'Pipfile').write_text('[packages]\n')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'apps/worker')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Python'])
            self.assertEqual(report['workspaces'][0]['manifests'], [{'file': 'Pipfile', 'ecosystem': 'Python'}])

    def test_visual_basic_project_and_case_insensitive_extension(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / 'services' / 'legacy'
            nested.mkdir(parents=True)
            (nested / 'Legacy.VBPROJ').write_text('<Project />')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['.NET'])
            self.assertEqual(report['workspaces'][0]['manifests'], [{'file': 'Legacy.VBPROJ', 'ecosystem': '.NET'}])


if __name__ == '__main__':
    unittest.main()
