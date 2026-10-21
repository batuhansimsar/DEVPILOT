"""Reject invalid manifest read arguments before touching the filesystem."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class BoundedReadArgumentTests(unittest.TestCase):
    def test_invalid_budgets_fail_closed_without_filesystem_access(self):
        path = Path('/nonexistent/manifest.toml')
        for budget in (True, False, None, -1, 1.5, float('inf'), '1024', object()):
            with self.subTest(budget=repr(budget)):
                with patch.object(Path, 'lstat', side_effect=AssertionError('unexpected lstat')):
                    self.assertIsNone(read_bounded_regular_file(path, budget))

    def test_embedded_nul_path_fails_closed(self):
        self.assertIsNone(read_bounded_regular_file(Path('secret\\x00manifest.toml'), 32))

    def test_invalid_path_type_fails_closed(self):
        self.assertIsNone(read_bounded_regular_file(None, 32))

    def test_zero_byte_budget_only_allows_empty_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'manifest.toml'
            path.write_bytes(b'')
            self.assertEqual(read_bounded_regular_file(path, 0), b'')
            path.write_bytes(b'x')
            self.assertIsNone(read_bounded_regular_file(path, 0))


if __name__ == '__main__':
    unittest.main()
