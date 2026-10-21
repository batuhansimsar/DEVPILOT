"""Regression coverage for incomplete Git diagnostic capture."""

import unittest

from devpilot.git_output import format_git_status


class GitStderrTruncationTests(unittest.TestCase):
    def test_success_with_truncated_stderr_is_not_silent(self):
        report = {
            'stdout': '## main\n', 'stderr': '', 'exit_code': 0,
            'stdout_truncated': False, 'stderr_truncated': True,
        }
        self.assertEqual(format_git_status(report),
                         '## main\nWarning: Git diagnostic output truncated; details may be incomplete')

    def test_failed_command_warns_and_safely_displays_partial_diagnostics(self):
        report = {
            'stdout': '', 'stderr': 'fatal: error\n?? forged\x1b[2J',
            'exit_code': 128, 'stderr_truncated': True,
        }
        rendered = format_git_status(report)
        self.assertIn('Warning: Git diagnostic output truncated', rendered)
        self.assertIn('Git status failed (exit code 128)', rendered)
        self.assertIn(r'fatal: error\x0a?? forged\x1b[2J', rendered)
        self.assertNotIn('\x1b', rendered)

    def test_untruncated_status_remains_unchanged(self):
        self.assertEqual(format_git_status({
            'stdout': '## main\n', 'exit_code': 0,
            'stdout_truncated': False, 'stderr_truncated': False,
        }), '## main\n')


if __name__ == '__main__':
    unittest.main()
