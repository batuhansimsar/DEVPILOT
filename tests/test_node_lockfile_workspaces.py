"""pnpm and Yarn lockfiles must identify Node.js workspaces on their own."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class NodeLockfileWorkspaceTests(unittest.TestCase):
    def test_standalone_lockfile_is_recognized(self):
        for lockfile in ('pnpm-lock.yaml', 'yarn.lock'):
            with self.subTest(lockfile=lockfile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / lockfile).touch()
                report = discover_workspaces(root)
                self.assertFalse(report['truncated'])
                self.assertEqual(report['workspace_count'], 1)
                self.assertEqual(report['workspaces'][0]['path'], '.')
                self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])
                self.assertEqual(report['workspaces'][0]['manifests'], [
                    {'file': lockfile, 'ecosystem': 'Node.js'},
                ])

    def test_mixed_manifests_remain_single_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{}', encoding='utf-8')
            (root / 'pnpm-lock.yaml').touch()
            (root / 'yarn.lock').touch()
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])
            self.assertEqual([item['file'] for item in report['workspaces'][0]['manifests']],
                             ['package.json', 'pnpm-lock.yaml', 'yarn.lock'])

    def test_symlinked_lockfiles_are_ignored(self):
        for lockfile in ('pnpm-lock.yaml', 'yarn.lock'):
            with self.subTest(lockfile=lockfile), tempfile.TemporaryDirectory() as directory, \
                    tempfile.TemporaryDirectory() as outside:
                target = Path(outside) / lockfile
                target.touch()
                try:
                    (Path(directory) / lockfile).symlink_to(target)
                except (OSError, NotImplementedError):
                    self.skipTest('symlinks unsupported')
                self.assertEqual(discover_workspaces(Path(directory))['workspace_count'], 0)

    def test_nested_lockfile_respects_depth_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'app'
            nested.mkdir()
            (nested / 'yarn.lock').touch()
            self.assertTrue(discover_workspaces(root, max_depth=0)['truncated'])
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspaces'][0]['path'], 'app')


if __name__ == '__main__':
    unittest.main()
