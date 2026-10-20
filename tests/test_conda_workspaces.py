"""Conda environment specifications identify otherwise manifest-free projects."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class CondaWorkspaceTests(unittest.TestCase):
    def test_environment_variants_at_root_and_nested(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'environment.yml').write_text('name: analytics\n')
            nested = root / 'examples' / 'training'
            nested.mkdir(parents=True)
            (nested / 'environment.yaml').write_text('name: training\n')
            (nested / 'environment.yml.bak').write_text('ignored\n')
            report = discover_workspaces(root)

        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual(
            [(w['path'], w['ecosystems'], w['manifests']) for w in report['workspaces']],
            [
                ('.', ['Conda'], [{'file': 'environment.yml', 'ecosystem': 'Conda'}]),
                ('examples/training', ['Conda'], [{'file': 'environment.yaml', 'ecosystem': 'Conda'}]),
            ],
        )

    def test_conda_and_python_manifests_share_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'environment.yml').write_text('name: analytics\n')
            (root / 'pyproject.toml').write_text('[project]\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Conda', 'Python'])

    def test_symlinked_conda_manifest_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            target = Path(outside) / 'environment.yml'
            target.write_text('name: secret\n')
            try:
                (root / 'environment.yml').symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
