"""NULs cannot be valid in Git's line-delimited porcelain v1 output."""

import unittest

from devpilot.git_state import is_git_dirty


class GitPorcelainNulTests(unittest.TestCase):
    def test_nul_in_header_cannot_prove_clean(self):
        for output in ('## main\x00unknown\n', '## main\n\x00', '## main\x00 M modified.py\n'):
            with self.subTest(output=repr(output)):
                self.assertIsNone(is_git_dirty(output, 0))

    def test_nul_in_path_or_ignored_record_is_inconclusive(self):
        for output in ('## main\n!! hidden\x00status\n',
                       '## main\n M altered\x00name.py\n',
                       '## main\n?? changed\x00filename\n'):
            with self.subTest(output=repr(output)):
                self.assertIsNone(is_git_dirty(output, 0))

    def test_legitimate_statuses_remain_classified(self):
        self.assertIs(is_git_dirty('## main\n', 0), False)
        self.assertIs(is_git_dirty('## main\n!! cache/\n', 0), False)
        self.assertIs(is_git_dirty('## main\n M modified.py\n', 0), True)
        self.assertIs(is_git_dirty('fragment\n?? new.py\n', 0), True)
        self.assertIs(is_git_dirty('## main\r\n', 0), False)


if __name__ == '__main__':
    unittest.main()
