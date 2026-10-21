"""Invalid runner stdout cannot masquerade as valid Git porcelain records."""

import unittest

from devpilot.git_output import format_git_status


class GitInvalidStdoutTests(unittest.TestCase):
    def test_non_text_stdout_is_not_displayed_as_git_status(self):
        for value in (b'## main\n', {'stdout': '## main'}, [b'## main'], 42, False):
            with self.subTest(value=value):
                output = format_git_status({'exit_code': 0, 'stdout': value, 'dirty': False})
                self.assertEqual(output, 'Git status unavailable (invalid porcelain output)')
                self.assertNotIn('No changes', output)

    def test_invalid_stdout_does_not_call_arbitrary_string_conversion(self):
        class MaliciousStdout:
            def __str__(self):
                raise RuntimeError('untrusted __str__ should not execute')

        self.assertEqual(
            format_git_status({'stdout': MaliciousStdout(), 'exit_code': 0}),
            'Git status unavailable (invalid porcelain output)',
        )

    def test_empty_string_cannot_establish_clean_status(self):
        self.assertEqual(format_git_status({'stdout': '', 'exit_code': 0, 'dirty': False}),
                         'Git status unavailable (empty porcelain output)')


if __name__ == '__main__':
    unittest.main()
