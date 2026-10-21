"""Whitespace-only Git stdout must not be mistaken for a complete status."""

import unittest

from devpilot.git_output import format_git_status


class GitBlankPorcelainTests(unittest.TestCase):
    def test_successful_blank_porcelain_is_inconclusive(self):
        for stdout in ('\n', '\r\n', '  ', '\t\n'):
            with self.subTest(stdout=repr(stdout)):
                self.assertEqual(
                    format_git_status({'stdout': stdout, 'exit_code': 0}),
                    'Git status unavailable (empty porcelain output)',
                )

    def test_blank_output_does_not_override_dirty_verdict(self):
        self.assertEqual(
            format_git_status({'stdout': ' \n', 'exit_code': 0, 'dirty': True}),
            'Git status reports changes but output is unavailable',
        )

    def test_blank_output_preserves_diagnostic_without_spoofed_records(self):
        self.assertEqual(
            format_git_status({'stdout': '\n', 'exit_code': 0, 'stderr': 'warn\n?? forged.txt'}),
            'Git status unavailable (empty porcelain output)\nwarn\\x0a?? forged.txt',
        )

    def test_valid_porcelain_is_unchanged(self):
        self.assertEqual(
            format_git_status({'stdout': '## main\n M app.py\n', 'exit_code': 0}),
            '## main\n M app.py\n',
        )


if __name__ == '__main__':
    unittest.main()
