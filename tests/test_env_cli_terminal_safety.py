"""Environment reports must never emit terminal control sequences."""

import unittest

from devpilot.env_cli import format_environment


class EnvironmentTerminalSafetyTests(unittest.TestCase):
    def test_missing_keys_cannot_inject_terminal_control_sequences(self):
        report = {'status': 'missing_keys',
                  'missing_keys': ['SAFE_KEY', 'BAD\x1b[31m\n\u202e']}
        message = format_environment(report)
        self.assertIn('SAFE_KEY', message)
        self.assertIn(r'BAD\x1b[31m\x0a\u202e', message)
        self.assertNotIn('\x1b', message)
        self.assertNotIn('\u202e', message)
        self.assertNotIn('\n', message)

    def test_template_and_error_fields_are_escaped_in_every_status(self):
        unsafe = '.env\x1b[2J\u202e'
        cases = [
            {'status': 'matched', 'template': unsafe, 'expected_count': 1},
            {'status': 'local_absent', 'template': unsafe, 'expected_count': 1},
            {'status': 'unreadable_local', 'template': unsafe,
             'detail': 'invalid\n\x1b[31m'},
        ]
        for report in cases:
            with self.subTest(status=report['status']):
                message = format_environment(report)
                self.assertIn(r'.env\x1b[2J\u202e', message)
                self.assertNotIn('\x1b', message)
                self.assertNotIn('\u202e', message)
                self.assertNotIn('\n', message)
                if report['status'] == 'unreadable_local':
                    self.assertIn(r'invalid\x0a\x1b[31m', message)

    def test_normal_metadata_is_preserved(self):
        self.assertEqual(
            format_environment({'status': 'missing_keys', 'missing_keys': ['A', 'B']}),
            'Environment: names missing from .env: A, B (may be supplied externally)',
        )


if __name__ == '__main__':
    unittest.main()
