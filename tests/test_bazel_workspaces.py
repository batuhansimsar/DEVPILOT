"""Bazel workspaces are recognized without reading or executing build files."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class BazelWorkspaceTests(unittest.TestCase):
    def test_bzlmod_and_legacy_bazel_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'MODULE.bazel').write_text('module(name = "root")\n')
            nested = root / 'third_party' / 'legacy'
            nested.mkdir(parents=True)
            (nested / 'WORKSPACE.bazel').write_text('workspace(name = "nested")\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual([(w['path'], w['ecosystems']) for w in report['workspaces']], [
            ('.', ['Bazel']), ('third_party/legacy', ['Bazel']),
        ])

    def test_legacy_workspace_and_module_are_one_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('MODULE.bazel', 'WORKSPACE', 'WORKSPACE.bazel', 'BUILD.bazel'):
                (root / name).write_text('')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['manifests'], [
            {'file': 'MODULE.bazel', 'ecosystem': 'Bazel'},
            {'file': 'WORKSPACE', 'ecosystem': 'Bazel'},
            {'file': 'WORKSPACE.bazel', 'ecosystem': 'Bazel'},
        ])

    def test_build_files_alone_are_not_workspace_roots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'BUILD').write_text('')
            (root / 'BUILD.bazel').write_text('')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_symlinked_module_manifest_is_ignored(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            target = Path(outside) / 'MODULE.bazel'
            target.write_text('module(name="external")')
            try:
                (root / 'MODULE.bazel').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_applies_to_bazel(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'nested').mkdir()
            (root / 'nested' / 'MODULE.bazel').write_text('')
            self.assertTrue(discover_workspaces(root, max_depth=0)['truncated'])
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
