"""Reject unsafe read arguments without attempting to access the filesystem."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class SafeFileReadInputsTests(unittest.TestCase):
    def test_invalid_budget_is_rejected_without_stat_or_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.toml'
            path.write_bytes(b'hello')
            with patch.object(Path, 'lstat') as inspect, patch('devpilot.safe_file_read.os.open') as open_file:
                for budget in (None, True, 4.0, -1, sys.maxsize, 2 ** 100):
                    with self.subTest(budget=budget):
                        self.assertIsNone(read_bounded_regular_file(path, budget))
                inspect.assert_not_called()
                open_file.assert_not_called()

    def test_invalid_path_is_rejected_without_open(self):
        with patch('devpilot.safe_file_read.os.open') as open_file:
            for path in (None, '', 123, Path('bad\x00name')):
                with self.subTest(path=repr(path)):
                    self.assertIsNone(read_bounded_regular_file(path, 100))
            open_file.assert_not_called()

    def test_zero_byte_budget_allows_only_empty_regular_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.toml'
            path.write_bytes(b'')
            self.assertEqual(read_bounded_regular_file(path, 0), b'')
            path.write_bytes(b'x')
            self.assertIsNone(read_bounded_regular_file(path, 0))


if __name__ == '__main__':
    unittest.main()
