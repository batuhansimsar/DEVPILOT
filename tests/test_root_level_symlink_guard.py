"""Regression coverage for root-level linked ancestor scan bypasses."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.scan_root import ensure_unlinked_scan_path
from devpilot.walk import walk_project


class RootLevelSymlinkGuardTests(unittest.TestCase):
    def _alias_paths(self):
        alias = Path(Path.cwd().anchor) / 'devpilot-untrusted-alias'
        return alias, alias / 'nested-repository'

    def test_root_level_symlinked_ancestor_is_rejected(self):
        alias, scan = self._alias_paths()
        with patch.object(Path, 'is_symlink', autospec=True,
                          side_effect=lambda candidate: candidate == alias):
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(scan)

    def test_walker_rejects_same_alias_before_scandir(self):
        alias, scan = self._alias_paths()
        problems = []
        with patch.object(Path, 'is_symlink', autospec=True,
                          side_effect=lambda candidate: candidate == alias), \
             patch('devpilot.walk.os.walk') as scanned:
            self.assertEqual(list(walk_project(scan, problems)), [])
            scanned.assert_not_called()
        self.assertEqual(problems, ['Cannot inspect .: project path contains a symbolic link'])

    def test_macos_system_alias_remains_usable_as_ancestor(self):
        alias = Path(Path.cwd().anchor) / 'var'
        scan = alias / 'folders' / 'workspace'
        with patch('devpilot.scan_root.sys.platform', 'darwin'), \
             patch.object(Path, 'is_symlink', autospec=True,
                          side_effect=lambda candidate: candidate == alias):
            ensure_unlinked_scan_path(scan)
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias)

    def test_non_macos_system_alias_is_not_exempted(self):
        alias = Path(Path.cwd().anchor) / 'var'
        with patch('devpilot.scan_root.sys.platform', 'linux'), \
             patch.object(Path, 'is_symlink', autospec=True,
                          side_effect=lambda candidate: candidate == alias):
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias / 'project')

    def test_regular_project_walk_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app.py').write_text('pass\n', encoding='utf-8')
            problems = []
            walked = list(walk_project(root, problems))
            self.assertEqual(problems, [])
            self.assertEqual(len(walked), 1)
            self.assertIn('app.py', walked[0][2])


if __name__ == '__main__':
    unittest.main()
