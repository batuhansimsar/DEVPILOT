"""Keep simultaneous Git capture errors and stderr visible without spoofing."""

import unittest

from devpilot.git_output import format_git_status


class MultipleGitDiagnosticTests(unittest.TestCase):
    def test_failed_git_preserves_both_distinct_diagnostics_safely(self):
        rendered = format_git_status({
            'exit_code': 128,
            'stdout': '## main\n',
            'error': 'capture failed\n?? forged.txt',
            'stderr': 'fatal: bad worktree\x1b[2J',
        })
        self.assertEqual(
            rendered,
            '## main\nGit status failed (exit code 128)\n'
            'capture failed\\x0a?? forged.txt\nfatal: bad worktree\\x1b[2J',
        )
        self.assertNotIn('\x1b', rendered)

    def test_success_preserves_stderr_and_capture_warning(self):
        rendered = format_git_status({
            'exit_code': 0, 'stdout': '## main\n', 'dirty': False,
            'error': 'partial capture', 'stderr': 'warning: config\rreset',
        })
        self.assertEqual(
            rendered,
            '## main\nGit diagnostic: partial capture\n'
            'Git diagnostic: warning: config\\x0dreset',
        )

    def test_duplicate_diagnostics_render_once(self):
        rendered = format_git_status({
            'exit_code': 128, 'error': 'fatal: same', 'stderr': 'fatal: same',
        })
        self.assertEqual(rendered, 'Git status failed (exit code 128)\nfatal: same')

    def test_missing_exit_code_preserves_stdout_precedence(self):
        self.assertEqual(format_git_status({
            'stdout': '## main\n', 'error': 'capture warning', 'stderr': 'warning',
        }), '## main\n')

    def test_no_stdout_retains_both_diagnostics(self):
        self.assertEqual(format_git_status({
            'error': 'spawn failure', 'stderr': 'fatal: failed',
        }), 'spawn failure\nfatal: failed')
