"""Regression tests for Go multi-module workspace discovery."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class GoWorkspaceDetectionTests(unittest.TestCase):
    def test_go_work_is_a_workspace_manifest(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'go.work').write_text('go 1.23\nuse ./module\n')
            (root / 'module').mkdir()
            (root / 'module' / 'go.mod').write_text('module example.com/module\n')
            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 2)
            self.assertEqual(
                [(w['path'], w['manifests'][0]['file']) for w in result['workspaces']],
                [('.', 'go.work'), ('module', 'go.mod')],
            )

    def test_go_work_symlink_is_not_followed(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            source = Path(outside) / 'go.work'
            source.write_text('go 1.23\n')
            try:
                (root / 'go.work').symlink_to(source)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks are unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
