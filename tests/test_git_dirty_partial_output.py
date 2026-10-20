"""An incomplete Git status must never prove the worktree is clean."""

import unittest

from devpilot.git_state import is_git_dirty


class GitDirtyPartialOutputTests(unittest.TestCase):
    def test_complete_header_can_prove_clean(self):
        for header in ('## main\n', '## No commits yet on main\n', '## main...origin/main\r\n'):
            with self.subTest(header=header):
                self.assertIs(is_git_dirty(header, 0), False)

    def test_partial_or_malformed_branch_only_output_is_unknown(self):
        for output in ('## main', '## \n', '## main\n\n',
                       '## main\n## another\n', '## main\n##',
                       '## main\n   '):
            with self.subTest(output=output):
                self.assertIsNone(is_git_dirty(output, 0))

    def test_dirty_tail_is_identified_without_header(self):
        for output in (' M app.py\n', 'fragment\n M app.py\n',
                       '## main\n?? new.txt'):
            with self.subTest(output=output):
                self.assertIs(is_git_dirty(output, 0), True)

    def test_failed_command_cannot_prove_clean(self):
        self.assertIsNone(is_git_dirty('## main\n', 128))
        self.assertIsNone(is_git_dirty(' M app.py\n', None))


if __name__ == '__main__':
    unittest.main()
