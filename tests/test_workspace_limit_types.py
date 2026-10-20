"""Workspace traversal limits must be explicit bounded integers."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class WorkspaceLimitTypeTests(unittest.TestCase):
    def test_boolean_limits_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for option in ({'max_depth': True}, {'max_depth': False},
                           {'max_directories': True}, {'max_directories': False}):
                with self.subTest(option=option), self.assertRaisesRegex(ValueError, 'Invalid scan limits'):
                    discover_workspaces(Path(directory), **option)

    def test_fractional_and_string_limits_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for option in ({'max_depth': 1.5}, {'max_directories': 2.5},
                           {'max_depth': '2'}, {'max_directories': '2'}):
                with self.subTest(option=option), self.assertRaisesRegex(ValueError, 'Invalid scan limits'):
                    discover_workspaces(Path(directory), **option)

    def test_zero_depth_remains_legal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'go.mod').write_text('module example.com/demo', encoding='utf-8')
            result = discover_workspaces(root, max_depth=0, max_directories=1)
        self.assertEqual(result['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
