"""Regression coverage for pnpm-only workspace discovery."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class PnpmWorkspaceTests(unittest.TestCase):
    def test_pnpm_workspace_without_package_json_discovered(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pnpm-workspace.yaml').write_text('packages: []')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], '.')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])
            self.assertEqual(report['workspaces'][0]['manifests'], [
                {'file': 'pnpm-workspace.yaml', 'ecosystem': 'Node.js'}
            ])

    def test_pnpm_workspace_symlink_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as other:
            root = Path(temp)
            target = Path(other) / 'pnpm-workspace.yaml'
            target.write_text('packages: []')
            try:
                (root / 'pnpm-workspace.yaml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlink unsupported')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
