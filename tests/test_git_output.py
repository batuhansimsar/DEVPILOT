"""Git CLI display must never pass raw escape controls to the terminal."""

import unittest

from devpilot.git_output import format_git_status


class GitOutputTests(unittest.TestCase):
    def test_status_controls_are_escaped_without_losing_record_boundaries(self):
        report = {'stdout': '## main\n?? name\x1b[2J\u202ereverse\r.txt\n'}
        rendered = format_git_status(report)
        self.assertEqual(rendered, '## main\n?? name\\x1b[2J\\u202ereverse\\x0d.txt\n')
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)
        self.assertNotIn('\r', rendered)

    def test_git_errors_are_escaped(self):
        self.assertEqual(format_git_status({'stderr': 'fatal: path\x1b[31m'}),
                         r'fatal: path\x1b[31m')
        self.assertEqual(format_git_status({'error': 'bad\x07'}), r'bad\x07')

    def test_normal_status_and_missing_output(self):
        self.assertEqual(format_git_status({'stdout': '## main\n M README.md\n'}),
                         '## main\n M README.md\n')
        self.assertEqual(format_git_status({}), 'No changes')
        self.assertEqual(format_git_status({'stdout': '## café\n'}), '## café\n')


if __name__ == '__main__':
    unittest.main()
