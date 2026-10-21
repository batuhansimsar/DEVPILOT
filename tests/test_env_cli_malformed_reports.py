"""Malformed external environment reports cannot crash or spoof CLI diagnostics."""

import unittest

from devpilot.env_cli import format_environment


class MalformedEnvironmentReportsTests(unittest.TestCase):
    def test_missing_required_fields_fail_closed(self):
        for report in (
            None, [], {}, {'status': None}, {'status': 'unexpected'},
            {'status': 'matched'}, {'status': 'local_absent'},
            {'status': 'unreadable_local', 'template': '.env'},
            {'status': 'missing_keys'}, {'status': 'missing_keys', 'missing_keys': []},
        ):
            with self.subTest(report=report):
                self.assertEqual(format_environment(report),
                                 'Environment: invalid environment report')

    def test_untrusted_field_types_are_not_iterated_or_stringified(self):
        class Dangerous:
            def __iter__(self):
                raise AssertionError('untrusted iterable executed')

            def __str__(self):
                raise AssertionError('untrusted string conversion executed')

        for report in (
            {'status': Dangerous()},
            {'status': 'matched', 'template': Dangerous(), 'expected_count': 1},
            {'status': 'missing_keys', 'missing_keys': Dangerous()},
            {'status': 'missing_keys', 'missing_keys': [Dangerous()]},
            {'status': 'unreadable_template', 'template': '.env.example', 'detail': Dangerous()},
        ):
            with self.subTest(keys=tuple(report)):
                self.assertEqual(format_environment(report),
                                 'Environment: invalid environment report')

    def test_valid_messages_and_terminal_escaping_are_preserved(self):
        self.assertEqual(format_environment({'status': 'missing_keys', 'missing_keys': ['A', 'B']}),
                         'Environment: names missing from .env: A, B (may be supplied externally)')
        self.assertIn('all 1 names', format_environment({
            'status': 'matched', 'template': '.env.example', 'expected_count': 1}))
        self.assertIn('no .env.example', format_environment({'status': 'no_template'}))
        output = format_environment({'status': 'missing_keys',
                                     'missing_keys': ['SAFE', 'BAD\x1b[31m\n']})
        self.assertIn(r'BAD\x1b[31m\x0a', output)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\n', output)


if __name__ == '__main__':
    unittest.main()
