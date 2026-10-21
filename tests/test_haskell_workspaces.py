"""Regression tests for Haskell Cabal and Stack workspace detection."""

import tempfile
import unittest
from pathlib import Path

from devpilot.haskell_manifests import is_haskell_manifest
from devpilot.workspaces import discover_workspaces


class HaskellManifestTests(unittest.TestCase):
    def test_recognizes_cabal_stack_and_lockfile_markers(self):
        for name in (
            'cabal.project', 'cabal.project.freeze', 'stack.yaml',
            'stack.yaml.lock', 'my-lib.cabal', 'a.cabal', 'Lib123.cabal',
        ):
            with self.subTest(name=name):
                self.assertTrue(is_haskell_manifest(name))

    def test_rejects_backups_and_non_cabal_names(self):
        for name in (
            'lib.cabal.bak', 'lib.cabal~', 'lib.CABAL', '.cabal',
            '-lib.cabal', 'lib-.cabal', 'lib_test.cabal',
            'cabal.project.local', 'stack.yaml.old', 'notstack.yaml',
            'lib.cabal/extra', 'K.cabal', '', None, 42,
        ):
            with self.subTest(name=name):
                self.assertFalse(is_haskell_manifest(name))

    def test_discovers_root_and_nested_haskell_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'cabal.project').write_text('')
            (root / 'nested').mkdir()
            (root / 'nested' / 'my-lib.cabal').write_text('')
            (root / 'nested' / 'stack.yaml').write_text('')
            (root / 'other').mkdir()
            (root / 'other' / 'my-lib.cabal.bak').write_text('')
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 2)
            self.assertEqual(
                [(entry['path'], entry['ecosystems']) for entry in report['workspaces']],
                [('.', ['Haskell']), ('nested', ['Haskell'])],
            )
            self.assertEqual(
                [m['file'] for m in report['workspaces'][1]['manifests']],
                ['my-lib.cabal', 'stack.yaml'],
            )

    def test_does_not_follow_symlinked_haskell_manifest(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'outside.cabal'
            target.write_text('')
            try:
                (root / 'outside.cabal').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_respects_depth_limit_for_haskell_markers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'project').mkdir()
            (root / 'project' / 'stack.yaml').write_text('')
            self.assertTrue(discover_workspaces(root, max_depth=0)['truncated'])
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
