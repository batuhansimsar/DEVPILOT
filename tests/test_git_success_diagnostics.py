"""Git warnings must not disappear merely because porcelain status succeeded."""

import unittest

from devpilot.git_output import format_git_status


class GitSuccessDiagnosticsTests(unittest.TestCase):
    def test_successful_clean_status_retains_sanitized_stderr(self):
        report = {
            'exit_code': 0, 'dirty': False, 'stdout': '## main\n',
            'stderr': 'warning: config\n?? forged.txt\x1b[2J',
        }
        rendered = format_git_status(report)
        self.assertEqual(rendered, '## main\nGit diagnostic: warning: config\\x0a?? forged.txt\\x1b[2J')
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('config\n??', rendered)

    def test_inconclusive_status_also_keeps_stderr(self):
        report = {'exit_code': 0, 'dirty': None, 'stdout': '## HEAD (no branch)\n',
                  'stderr': 'warning: scan incomplete'}
        rendered = format_git_status(report)
        self.assertIn('worktree state inconclusive', rendered)
        self.assertIn('Git diagnostic: warning: scan incomplete', rendered)

    def test_no_diagnostic_does_not_add_output(self):
        self.assertEqual(format_git_status({'exit_code': 0, 'dirty': False, 'stdout': '## main\n'}), '## main\n')

    def test_failed_status_does_not_duplicate_diagnostic(self):
        rendered = format_git_status({'exit_code': 128, 'stdout': '## main\n', 'stderr': 'fatal: bad repo'})
        self.assertEqual(rendered.count('fatal: bad repo'), 1)
        self.assertNotIn('Git diagnostic:', rendered)


if __name__ == '__main__':
    unittest.main()
