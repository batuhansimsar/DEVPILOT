"""Haskell workspace marker and project discovery regression tests."""

import tempfile
import unittest
from pathlib import Path

from devpilot.haskell_manifests import is_haskell_manifest


class HaskellManifestTests(unittest.TestCase):
    def test_stack_cabal_and_hpack_markers(self):
        for filename in ('stack.yaml', 'cabal.project', 'cabal.project.freeze',
                         'package.yaml', 'my-lib.cabal', 'Project42.cabal'):
            with self.subTest(filename=filename):
                self.assertTrue(is_haskell_manifest(filename))

    def test_backups_lookalikes_and_invalid_names(self):
        for filename in ('stack.yaml.bak', 'Stack.yaml', 'package.yml',
                         'cabal.project.local', 'my-lib.cabal~', 'foo.cabal.txt',
                         '.cabal', '-foo.cabal', 'foo-.cabal', 'foo--bar.cabal',
                         'foo_bar.cabal', 'foo.cabal.bak', 'README.md',
                         'src/Main.hs', ''):
            with self.subTest(filename=filename):
                self.assertFalse(is_haskell_manifest(filename))
        for value in (None, 12, b'stack.yaml'):
            with self.subTest(value=value):
                self.assertFalse(is_haskell_manifest(value))


class HaskellDiscoveryIntegrationTests(unittest.TestCase):
    def test_detection_analysis_and_nested_workspaces(self):
        from devpilot.core import analyze_project, detect_projects, test_commands
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'stack.yaml').write_text('resolver: lts-22.0\n')
            (root / 'my-lib.cabal').write_text('name: my-lib\n')
            (root / 'Main.hs').write_text('module Main where\n')
            nested = root / 'packages' / 'util'
            nested.mkdir(parents=True)
            (nested / 'cabal.project').write_text('packages: .\n')
            (nested / 'fake.cabal.bak').write_text('backup\n')
            self.assertIn('Haskell', detect_projects(root))
            self.assertIn({'ecosystem': 'Haskell', 'argv': ['stack', 'test'],
                           'reason': 'stack.yaml'}, test_commands(root))
            summary = analyze_project(root)
            self.assertIn('Haskell', summary['project_types'])
            self.assertEqual(summary['languages']['Haskell'], 1)
            self.assertIn('my-lib.cabal', summary['key_files'])
            self.assertNotIn('fake.cabal.bak', summary['key_files'])
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual([(w['path'], w['ecosystems']) for w in report['workspaces']],
                             [('.', ['Haskell']), ('packages/util', ['Haskell'])])
            self.assertEqual([m['file'] for m in report['workspaces'][0]['manifests']],
                             ['my-lib.cabal', 'stack.yaml'])

    def test_cabal_only_suggests_cabal_test(self):
        from devpilot.core import test_commands

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'my-lib.cabal').write_text('name: my-lib\n')
            self.assertIn({'ecosystem': 'Haskell', 'argv': ['cabal', 'test'],
                           'reason': 'Cabal project'}, test_commands(root))

    def test_symlinked_cabal_manifest_is_not_scanned(self):
        from devpilot.core import detect_projects
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            target = Path(outside) / 'hidden.cabal'
            target.write_text('name: hidden\n')
            try:
                (root / 'hidden.cabal').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('Haskell', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_directory_depth_limit(self):
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'nested').mkdir()
            (root / 'nested' / 'package.yaml').write_text('name: nested\n')
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertTrue(discover_workspaces(root, max_depth=0)['truncated'])
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
