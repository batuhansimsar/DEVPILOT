"""Failed or truncated Git inspections must not look like clean status output."""

import unittest

from devpilot.git_output import format_git_status


class GitOutputCompletenessTests(unittest.TestCase):
    def test_truncated_branch_header_warns_instead_of_appearing_clean(self):
        rendered = format_git_status({
            'stdout': '## main\n', 'exit_code': 0, 'stdout_truncated': True,
        })
        self.assertEqual(rendered,
                         '## main\nWarning: Git status output truncated; results may be incomplete')

    def test_truncated_change_preserves_safe_records_and_warns(self):
        rendered = format_git_status({
            'stdout': '## main\n?? name\x1b[2J\n', 'exit_code': 0,
            'stdout_truncated': True,
        })
        self.assertIn('?? name\\x1b[2J\nWarning:', rendered)
        self.assertNotIn('\x1b', rendered)

    def test_failure_without_diagnostic_is_not_no_changes(self):
        self.assertEqual(format_git_status({'exit_code': 128, 'stdout': ''}),
                         'Git status failed (exit code 128)')
        self.assertEqual(format_git_status({'exit_code': None}),
                         'Git status unavailable (command did not complete)')

    def test_failed_command_with_stdout_and_error_displays_both_safely(self):
        rendered = format_git_status({
            'stdout': '## main\n', 'exit_code': 128,
            'stderr': 'fatal: failed\n?? forged\x1b[2J',
        })
        self.assertEqual(rendered,
                         '## main\nGit status failed (exit code 128)\n'
                         'fatal: failed\\x0a?? forged\\x1b[2J')
        self.assertNotIn('\x1b', rendered)
        self.assertEqual(rendered.count('\n'), 2)

    def test_inconclusive_dirty_state_is_not_rendered_as_clean(self):
        self.assertEqual(format_git_status({
            'stdout': '## main\n', 'exit_code': 0, 'dirty': None,
        }), '## main\nGit status unavailable (worktree state inconclusive)')

    def test_normal_complete_output_remains_unchanged(self):
        self.assertEqual(format_git_status({
            'stdout': '## main\n', 'exit_code': 0, 'stdout_truncated': False,
        }), '## main\n')


if __name__ == '__main__':
    unittest.main()
