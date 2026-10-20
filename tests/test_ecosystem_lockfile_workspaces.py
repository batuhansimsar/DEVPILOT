"""Lockfiles alone signal Swift, Dart and Elixir workspaces."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class EcosystemLockfileWorkspaceTests(unittest.TestCase):
    def test_nested_lockfile_only_workspaces(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for folder, filename in (
                ('ios', 'Package.resolved'),
                ('mobile', 'pubspec.lock'),
                ('service', 'mix.lock'),
            ):
                path = root / folder
                path.mkdir()
                (path / filename).write_text('')
            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 3)
            self.assertEqual(
                [(w['path'], w['ecosystems']) for w in result['workspaces']],
                [('ios', ['Swift']), ('mobile', ['Dart']), ('service', ['Elixir'])],
            )
            self.assertFalse(result['truncated'])

    def test_manifest_and_lockfile_are_one_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for filename in ('pubspec.yaml', 'pubspec.lock'):
                (root / filename).write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(
                [m['file'] for m in report['workspaces'][0]['manifests']],
                ['pubspec.lock', 'pubspec.yaml'],
            )

    def test_symlinked_lockfile_is_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            target = Path(outside) / 'mix.lock'
            target.write_text('')
            try:
                (root / 'mix.lock').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlink unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_still_applies(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'inner').mkdir()
            (root / 'inner' / 'Package.resolved').write_text('')
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
