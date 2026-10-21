"""Julia workspace discovery by project and versioned manifest filenames."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class JuliaWorkspaceTests(unittest.TestCase):
    def test_standard_and_alternative_julia_project_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Project.toml').write_text('')
            (root / 'Manifest.toml').write_text('')
            nested = root / 'packages' / 'math'
            nested.mkdir(parents=True)
            (nested / 'JuliaProject.toml').write_text('')
            (nested / 'JuliaManifest.toml').write_text('')

            result = discover_workspaces(root)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['workspace_count'], 2)
            self.assertEqual([w['path'] for w in result['workspaces']],
                             ['.', 'packages/math'])
            self.assertEqual([w['ecosystems'] for w in result['workspaces']],
                             [['Julia'], ['Julia']])
            self.assertEqual(
                [[m['file'] for m in w['manifests']] for w in result['workspaces']],
                [['Manifest.toml', 'Project.toml'],
                 ['JuliaManifest.toml', 'JuliaProject.toml']],
            )

    def test_versioned_manifest_alone_is_a_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Manifest-v1.11.toml').write_text('')
            (root / 'Manifest-v1.10.toml').write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Julia'])
            self.assertEqual(
                [m['file'] for m in report['workspaces'][0]['manifests']],
                ['Manifest-v1.10.toml', 'Manifest-v1.11.toml'],
            )

    def test_malformed_and_backup_names_are_not_julia_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('Manifest-v1.toml', 'Manifest-v01.10.toml',
                         'Manifest-v1.010.toml', 'Manifest-v1.10.toml.bak',
                         'manifest-v1.10.toml', 'Project.toml.bak'):
                (root / name).write_text('')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_julia_manifest_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'Project.toml'
            target.write_text('')
            try:
                (root / 'Project.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
