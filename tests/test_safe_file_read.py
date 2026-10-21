"""Manifest reads must fail closed when untrusted filesystem nodes change."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class BoundedRegularFileTests(unittest.TestCase):
    def test_regular_files_and_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pubspec.yaml'
            path.write_bytes(b'hello')
            self.assertEqual(read_bounded_regular_file(path, 5), b'hello')
            self.assertIsNone(read_bounded_regular_file(path, 4))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO support is unavailable')
    def test_fifo_is_rejected_without_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pubspec.yaml'
            os.mkfifo(path)
            with patch('devpilot.safe_file_read.os.open') as opened:
                self.assertIsNone(read_bounded_regular_file(path, 50))
                opened.assert_not_called()

    def test_link_substitution_between_lstat_and_open(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'pubspec.yaml'
            outside = root / 'outside'
            outside.write_bytes(b'private data')
            path.write_bytes(b'original')
            real_open = os.open
            def replace(path_arg, flags):
                path.unlink()
                path.symlink_to(outside)
                return real_open(path_arg, flags)
            with patch('devpilot.safe_file_read.os.open', side_effect=replace):
                self.assertIsNone(read_bounded_regular_file(path, 50))

    def test_stable_utf8_manifest_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pubspec.yaml'
            data = b'name: app\ndependencies:\n  flutter:\n    sdk: flutter\n'
            path.write_bytes(data)
            self.assertEqual(read_bounded_regular_file(path, 128 * 1024), data)


if __name__ == '__main__':
    unittest.main()
