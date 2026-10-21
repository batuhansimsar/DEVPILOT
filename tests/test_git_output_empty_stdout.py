"""Git's mandatory branch header must not silently disappear on success."""

import unittest

from devpilot.git_output import format_git_status


class GitStatusEmptyOutputTests(unittest.TestCase):
    def test_success_with_missing_porcelain_output_is_inconclusive(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'stdout': ''}),
            'Git status unavailable (empty porcelain output)',
        )

    def test_clean_verdict_remains_compatible_with_existing_reports(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'stdout': '', 'dirty': False}),
            'No changes',
        )

    def test_valid_branch_header_does_not_add_warning(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'stdout': '## main\n'}),
            '## main\n',
        )

    def test_unknown_dirty_verdict_keeps_more_specific_warning(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'stdout': '', 'dirty': None}),
            'Git status unavailable (worktree state inconclusive)',
        )

    def test_escaped_diagnostic_is_preserved_on_failure(self):
        self.assertEqual(
            format_git_status({'exit_code': 128, 'stderr': 'fatal: \x1b[31m'}),
            r'Git status failed (exit code 128)' + '\n' + r'fatal: \x1b[31m',
        )


if __name__ == '__main__':
    unittest.main()
