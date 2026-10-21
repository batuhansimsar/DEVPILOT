"""Ensure dependency inventory root preflight cannot be bypassed via aliases."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.scan_root import ensure_unlinked_scan_path


class ScanRootTests(unittest.TestCase):
    def test_regular_nested_directory_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo' / 'src'
            root.mkdir(parents=True)
            ensure_unlinked_scan_path(root)

    def test_direct_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / 'target'
            target.mkdir()
            alias = base / 'alias'
            try:
                alias.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias)

    def test_symlinked_parent_is_rejected_even_if_target_exists(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            nested = base / 'outside' / 'nested'
            nested.mkdir(parents=True)
            alias = base / 'alias'
            try:
                alias.symlink_to(nested.parent, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias / 'nested')

    def test_dangling_symlinked_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            alias = base / 'alias'
            try:
                alias.symlink_to(base / 'missing', target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias / 'nested')


    def test_root_level_non_system_symlink_is_rejected(self):
        # Use a synthetic root link without writing into the filesystem anchor.
        anchor = Path(Path.cwd().anchor)
        alias = anchor / 'devpilot-synthetic-link'
        with patch.object(Path, 'is_symlink', lambda path: path == alias):
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias / 'repo')

    def test_only_standard_macos_alias_target_is_accepted(self):
        alias = Path('/var')
        with patch('devpilot.scan_root.sys.platform', 'darwin'), \
             patch.object(Path, 'is_symlink', lambda path: path == alias), \
             patch.object(Path, 'resolve', lambda path, strict=False: Path('/private/var')):
            ensure_unlinked_scan_path(alias / 'repo')

    def test_macos_alias_to_unexpected_target_is_rejected(self):
        alias = Path('/var')
        with patch('devpilot.scan_root.sys.platform', 'darwin'), \
             patch.object(Path, 'is_symlink', lambda path: path == alias), \
             patch.object(Path, 'resolve', lambda path, strict=False: Path('/other')):
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                ensure_unlinked_scan_path(alias / 'repo')

if __name__ == '__main__':
    unittest.main()
