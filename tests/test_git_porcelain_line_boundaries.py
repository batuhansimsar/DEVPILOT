"""Git porcelain uses LF records, not Python's Unicode line boundaries."""

import unittest

from devpilot.git_state import is_git_dirty


class GitPorcelainLineBoundaryTests(unittest.TestCase):
    def test_unicode_separators_inside_ignored_paths_do_not_forge_changes(self):
        for separator in ('\u0085', '\u2028', '\u2029', '\x0b', '\x0c'):
            with self.subTest(separator=repr(separator)):
                status = f'## main\n!! ignored{separator} M forged.py\n'
                self.assertIs(is_git_dirty(status, 0), False)

    def test_unicode_separators_are_valid_inside_branch_and_changed_names(self):
        self.assertIs(is_git_dirty('## topic\u2028feature\n', 0), False)
        self.assertIs(is_git_dirty('## main\n?? new\u2028file.py\n', 0), True)
        self.assertIs(is_git_dirty('## main\n!! ignored\u0085?? fake\n M real.py\n', 0), True)

    def test_embedded_carriage_return_is_unknown_but_crlf_is_valid(self):
        self.assertIsNone(is_git_dirty('## main\r M forged.py\n', 0))
        self.assertIs(is_git_dirty('## main\r\n!! ignored\r\n', 0), False)
        self.assertIs(is_git_dirty('## main\r\n M edited.py\r\n', 0), True)


if __name__ == '__main__':
    unittest.main()
