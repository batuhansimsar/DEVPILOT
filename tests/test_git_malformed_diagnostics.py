"""Git status must not stringify malformed runner diagnostics or exit codes."""

import unittest

from devpilot.git_output import format_git_status


class ExplosiveValue:
    def __str__(self):
        raise AssertionError('untrusted value was stringified')

    def __repr__(self):
        raise AssertionError('untrusted value was repr-formatted')

    def __bool__(self):
        raise AssertionError('untrusted value was truth-tested')

    def __eq__(self, other):
        raise AssertionError('untrusted value was compared')

    def __ne__(self, other):
        raise AssertionError('untrusted value was compared')


class MalformedGitDiagnosticsTests(unittest.TestCase):
    def test_malformed_diagnostics_cannot_crash_a_successful_report(self):
        for key, value in (('error', ExplosiveValue()), ('stderr', b'token=hidden')):
            with self.subTest(key=key):
                result = format_git_status({'exit_code': 0, 'stdout': '## main\n', key: value})
                self.assertEqual(result, '## main\nGit diagnostic: unreadable non-text diagnostic')
                self.assertNotIn('token=hidden', result)

    def test_nontext_diagnostics_are_deduplicated_without_stringifying(self):
        result = format_git_status({'exit_code': 128, 'error': ExplosiveValue(), 'stderr': ExplosiveValue()})
        self.assertEqual(result, 'Git status failed (exit code 128)\nunreadable non-text diagnostic')

    def test_malformed_exit_code_does_not_call_str(self):
        for value in (ExplosiveValue(), True, '128'):
            with self.subTest(type=type(value)):
                result = format_git_status({'exit_code': value, 'stdout': '## main\n'})
                self.assertEqual(result, '## main\nGit status unavailable (invalid exit code)')

    def test_malformed_stdout_cannot_force_boolean_conversion(self):
        result = format_git_status({'exit_code': 0, 'stdout': ExplosiveValue()})
        self.assertEqual(result, 'Git status unavailable (invalid porcelain output)')

    def test_normal_text_diagnostics_are_still_escaped(self):
        self.assertEqual(
            format_git_status({'exit_code': 0, 'stdout': '## main\n', 'stderr': 'warning\nnext\x1b'}),
            r'## main' + '\n' + r'Git diagnostic: warning\x0anext\x1b',
        )


if __name__ == '__main__':
    unittest.main()
