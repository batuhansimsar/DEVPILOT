"""Non-porcelain command results must never be reported as a clean worktree."""

import unittest

from devpilot.git_state import is_git_dirty


class GitStatusInputTypeTests(unittest.TestCase):
    def test_invalid_stream_types_are_inconclusive(self):
        for stdout in (None, b'## main\n', False, {}, ['## main\n']):
            with self.subTest(type=type(stdout).__name__):
                self.assertIsNone(is_git_dirty(stdout, 0))

    def test_invalid_exit_status_types_are_inconclusive(self):
        for status in (False, True, 0.0, '0', None):
            with self.subTest(status=repr(status)):
                self.assertIsNone(is_git_dirty('## main\n', status))

    def test_real_success_still_detects_clean_or_dirty(self):
        self.assertIs(is_git_dirty('## main\n', 0), False)
        self.assertIs(is_git_dirty('## main\n?? README.md\n', 0), True)
        self.assertIsNone(is_git_dirty('## main', 0))
        self.assertIsNone(is_git_dirty('## main\n', 1))


if __name__ == '__main__':
    unittest.main()
