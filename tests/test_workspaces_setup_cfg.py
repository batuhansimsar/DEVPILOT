"""Setuptools projects may use setup.cfg without setup.py or pyproject.toml."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class SetupCfgWorkspaceTests(unittest.TestCase):
    def test_root_and_nested_setup_cfg_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'setup.cfg').write_text('[metadata]\nname = root\n')
            nested = root / 'packages' / 'worker'
            nested.mkdir(parents=True)
            (nested / 'setup.cfg').write_text('[metadata]\nname = worker\n')
            (nested / 'setup.cfg.bak').write_text('backup')
            report = discover_workspaces(root)

        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual(
            [(w['path'], w['ecosystems'], w['manifests']) for w in report['workspaces']],
            [
                ('.', ['Python'], [{'file': 'setup.cfg', 'ecosystem': 'Python'}]),
                ('packages/worker', ['Python'], [{'file': 'setup.cfg', 'ecosystem': 'Python'}]),
            ],
        )
        self.assertFalse(report['truncated'])

    def test_setup_cfg_coexists_with_pyproject_without_extra_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pyproject.toml').write_text('[build-system]\n')
            (root / 'setup.cfg').write_text('[metadata]\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Python'])
        self.assertEqual([m['file'] for m in report['workspaces'][0]['manifests']],
                         ['pyproject.toml', 'setup.cfg'])

    def test_setup_cfg_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            target = Path(outside) / 'setup.cfg'
            target.write_text('[metadata]\n')
            try:
                (root / 'setup.cfg').symlink_to(target)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
