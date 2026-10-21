"""Absent Git results are inconclusive, never evidence of a clean tree."""

import unittest

from devpilot.git_output import format_git_status


class GitMissingResultTests(unittest.TestCase):
    def test_missing_result_is_not_a_clean_report(self):
        for report in ({}, {'stdout': ''}, {'dirty': False}, {'stdout': '', 'dirty': False}):
            with self.subTest(report=report):
                self.assertEqual(
                    format_git_status(report),
                    'Git status unavailable (missing command result)',
                )

    def test_successful_explicit_clean_verdict_is_preserved(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'dirty': False, 'stdout': ''}),
            'No changes',
        )

    def test_diagnostic_only_reporting_is_preserved(self):
        self.assertEqual(
            format_git_status({'error': 'fatal: missing repo\x1b[2J'}),
            r'fatal: missing repo\x1b[2J',
        )

    def test_present_porcelain_records_are_preserved(self):
        self.assertEqual(
            format_git_status({'stdout': '## main\n?? added.txt\n'}),
            '## main\n?? added.txt\n',
        )


if __name__ == '__main__':
    unittest.main()
