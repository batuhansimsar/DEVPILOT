"""Enforce Python's read-size bound before opening untrusted files."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class OverflowReadBudgetTests(unittest.TestCase):
    def test_oversized_budgets_do_not_stat_or_open_file(self):
        path = Path('not-inspected')
        for budget in (sys.maxsize, sys.maxsize + 1, 10 ** 100):
            with self.subTest(budget=budget), patch.object(Path, 'lstat') as lstat:
                self.assertIsNone(read_bounded_regular_file(path, budget))
                lstat.assert_not_called()

    def test_small_file_remains_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.txt'
            path.write_bytes(b'abc')
            self.assertEqual(read_bounded_regular_file(path, 3), b'abc')
            self.assertIsNone(read_bounded_regular_file(path, 2))


if __name__ == '__main__':
    unittest.main()
