"""Incomplete Git reports must keep actionable sanitized diagnostics."""

import unittest

from devpilot.git_output import format_git_status


class GitIncompleteDiagnosticsTests(unittest.TestCase):
    def test_inconclusive_empty_status_keeps_stderr(self):
        rendered = format_git_status({
            'exit_code': 0, 'dirty': None, 'stdout': '',
            'stderr': 'warning: cannot scan\n?? spoofed.txt',
        })
        self.assertEqual(rendered,
                         'Git status unavailable (worktree state inconclusive)\n'
                         'warning: cannot scan\\x0a?? spoofed.txt')

    def test_known_dirty_with_missing_output_keeps_capture_error(self):
        rendered = format_git_status({
            'exit_code': 0, 'dirty': True, 'stdout': '',
            'error': 'capture failed\x1b[2J',
        })
        self.assertEqual(rendered,
                         'Git status reports changes but output is unavailable\n'
                         'capture failed\\x1b[2J')

    def test_empty_success_keeps_both_distinct_diagnostics(self):
        rendered = format_git_status({
            'exit_code': 0, 'stdout': '',
            'error': 'buffer unavailable', 'stderr': 'fatal: no status',
        })
        self.assertEqual(rendered,
                         'Git status unavailable (empty porcelain output)\n'
                         'buffer unavailable\nfatal: no status')
