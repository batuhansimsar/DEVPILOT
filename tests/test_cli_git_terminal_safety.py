"""The Git command's human-readable CLI output must escape untrusted controls."""

import unittest

from devpilot.cli import _human


class GitCLISafetyTests(unittest.TestCase):
    def test_git_status_output_keeps_lines_but_escapes_terminal_controls(self):
        report = {'stdout': '## main\n?? secret\x1b[2J\u202emarker\n'}
        rendered = _human('git', report)
        self.assertEqual(rendered, '## main\n?? secret\\x1b[2J\\u202emarker\n')
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)

    def test_git_stderr_error_is_sanitized(self):
        self.assertEqual(_human('git', {'stdout': '', 'stderr': 'fatal\x1b[31m'}),
                         r'fatal\x1b[31m')


if __name__ == '__main__':
    unittest.main()
