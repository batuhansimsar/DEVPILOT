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

    def test_diagnostic_line_breaks_cannot_spoof_status_records(self):
        for key in ('error', 'stderr'):
            with self.subTest(key=key):
                diagnostic = 'fatal: cannot read\n## main\n?? forged.txt\r\x1b[2J'
                output = format_git_status({key: diagnostic})
                self.assertEqual(output,
                                 r'fatal: cannot read\x0a## main\x0a?? forged.txt\x0d\x1b[2J')
                self.assertNotIn('\n', output)
                self.assertNotIn('\r', output)
                self.assertNotIn('\x1b', output)

    def test_stdout_precedence_preserves_record_boundaries(self):
        report = {'stdout': '## main\n M file.txt\n', 'error': 'spoof\nerror'}
        self.assertEqual(format_git_status(report), '## main\n M file.txt\n')

    def test_normal_status_and_missing_output(self):
        self.assertEqual(format_git_status({'stdout': '## main\n M README.md\n'}),
                         '## main\n M README.md\n')
        self.assertEqual(format_git_status({}), 'No changes')
        self.assertEqual(format_git_status({'stdout': '## café\n'}), '## café\n')


    def test_failed_git_without_diagnostics_is_not_reported_clean(self):
        self.assertEqual(format_git_status({'exit_code': 128, 'stdout': '', 'stderr': ''}),
                         'Git status failed (exit code 128)')
        self.assertEqual(format_git_status({'exit_code': 0, 'dirty': None, 'stdout': ''}),
                         'Git status unavailable (worktree state inconclusive)')
        self.assertEqual(format_git_status({'exit_code': 0, 'dirty': False, 'stdout': ''}),
                         'No changes')

    def test_missing_stdout_must_not_hide_known_dirty_state(self):
        self.assertEqual(format_git_status({'exit_code': 0, 'dirty': True, 'stdout': ''}),
                         'Git status reports changes but output is unavailable')
        self.assertIn('Git status reports changes', format_git_status({
            'dirty': True, 'stdout': '', 'stdout_truncated': True,
        }))

    def test_git_failure_diagnostics_take_precedence(self):
        self.assertEqual(format_git_status({'exit_code': 128, 'stderr': 'fatal: no repository'}),
                         'Git status failed (exit code 128)\nfatal: no repository')


if __name__ == '__main__':
    unittest.main()
