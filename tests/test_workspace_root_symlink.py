"""Workspace discovery must not follow a symlink at the requested root."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class RootSymlinkTests(unittest.TestCase):
    def test_symlink_root_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            target = Path(external)
            (target / 'package.json').write_text('{}')
            alias = Path(directory) / 'linked-project'
            try:
                alias.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unavailable')
            report = discover_workspaces(alias)
            self.assertEqual(report['path'], str(alias))
            self.assertEqual(report['workspace_count'], 0)
            self.assertEqual(report['directories_scanned'], 0)
            self.assertTrue(report['truncated'])
            self.assertEqual(
                report['problems'],
                ['Cannot inspect .: project root is a symbolic link'],
            )

    def test_normal_root_still_discovers_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{}')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['problems'], [])
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])


if __name__ == '__main__':
    unittest.main()
