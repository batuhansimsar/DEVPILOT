"""Ensure dependency inventory root preflight cannot be bypassed via aliases."""

import tempfile
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
