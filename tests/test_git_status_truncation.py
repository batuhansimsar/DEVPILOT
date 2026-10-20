"""Incomplete Git status output must not produce a false dirty verdict."""

import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import git_status


class GitStatusTruncationTests(unittest.TestCase):
    def test_truncated_clean_header_is_unknown(self):
        with patch('devpilot.core.command_result', return_value={
            'stdout': '## main\n', 'stderr': '', 'exit_code': 0,
            'stdout_truncated': True,
        }):
            self.assertIsNone(git_status(Path('.'))['dirty'])

    def test_truncated_but_valid_change_is_dirty(self):
        with patch('devpilot.core.command_result', return_value={
            'stdout': '?? added.txt\n', 'stderr': '', 'exit_code': 0,
            'stdout_truncated': True,
        }):
            self.assertIs(git_status(Path('.'))['dirty'], True)

    def test_complete_clean_header_is_clean(self):
        with patch('devpilot.core.command_result', return_value={
            'stdout': '## main\n', 'stderr': '', 'exit_code': 0,
            'stdout_truncated': False,
        }):
            self.assertIs(git_status(Path('.'))['dirty'], False)


if __name__ == '__main__':
    unittest.main()
