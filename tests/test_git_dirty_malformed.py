"""Malformed Git status output must not be misclassified as changed files."""

import unittest

from devpilot.git_state import is_git_dirty


class GitDirtyMalformedTests(unittest.TestCase):
    def test_arbitrary_output_is_unknown(self):
        for content in ('unexpected diagnostic\n', '## main\nnot a status\n',
                        '## main\n M\n', '## main\n?? \n',
                        '## main\nXY invalid.txt\n'):
            with self.subTest(content=content):
                self.assertIsNone(is_git_dirty(content, 0))

    def test_real_change_detected_even_after_diagnostic_tail(self):
        for record in (' M app.py', 'M  tracked.py', '?? new.txt',
                       'UU conflicted.py', 'T  linked', 'R  old -> new'):
            with self.subTest(record=record):
                self.assertIs(is_git_dirty('fragment\n' + record + '\n', 0), True)

    def test_clean_header_is_still_clean(self):
        self.assertIs(is_git_dirty('## main\r\n', 0), False)


if __name__ == '__main__':
    unittest.main()
