"""Malformed capture flags must not hide lost Git output or execute hooks."""

import unittest

from devpilot.git_output import format_git_status


class _ExplosiveBool:
    def __bool__(self):
        raise AssertionError('untrusted flag was coerced to bool')

    def __str__(self):
        raise AssertionError('untrusted flag was rendered')


class GitOutputTruncationFlagsTests(unittest.TestCase):
    def test_real_truncation_flags_report_specific_warnings(self):
        output = format_git_status({
            'stdout': '## main\n', 'stdout_truncated': True,
            'stderr_truncated': True,
        })
        self.assertIn('Git status output truncated', output)
        self.assertIn('Git diagnostic output truncated', output)

    def test_malformed_capture_flags_do_not_run_custom_methods(self):
        for key in ('stdout_truncated', 'stderr_truncated'):
            with self.subTest(key=key):
                output = format_git_status({'stdout': '## main\n', key: _ExplosiveBool()})
                self.assertIn('invalid Git '+key+' flag', output)
                self.assertIn('output may be incomplete', output)

    def test_malformed_false_lookalikes_do_not_silence_warnings(self):
        for value in (None, 0, '', 'false', [], {}):
            with self.subTest(value=type(value).__name__):
                output = format_git_status({'stdout': '## main\n',
                                            'stdout_truncated': value})
                self.assertIn('invalid Git stdout_truncated flag', output)

    def test_explicit_false_flags_leave_clean_status_intact(self):
        self.assertEqual(format_git_status({
            'stdout': '## main\n', 'stdout_truncated': False,
            'stderr_truncated': False,
        }), '## main\n')


if __name__ == '__main__':
    unittest.main()
