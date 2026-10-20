"""Bundler and uv workspace markers are detected without project manifests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class WorkspaceLockfileMarkerTests(unittest.TestCase):
    def test_uv_lock_alone_identifies_python_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'uv.lock').write_text('version = 1\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Python'])
        self.assertEqual(report['workspaces'][0]['manifests'],
                         [{'file': 'uv.lock', 'ecosystem': 'Python'}])

    def test_bundler_markers_in_one_nested_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / 'apps' / 'ruby'
            nested.mkdir(parents=True)
            (nested / 'gems.rb').write_text('source "https://rubygems.org"\n')
            (nested / 'Gemfile.lock').write_text('GEM\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['path'], 'apps/ruby')
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Ruby'])
        self.assertEqual([m['file'] for m in report['workspaces'][0]['manifests']],
                         ['Gemfile.lock', 'gems.rb'])

    def test_symlinked_lockfile_is_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as external:
            root = Path(temp)
            target = Path(external) / 'uv.lock'
            target.write_text('version = 1\n')
            try:
                (root / 'uv.lock').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
