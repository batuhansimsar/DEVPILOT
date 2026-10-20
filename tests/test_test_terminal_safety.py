"""Untrusted test subprocess output cannot inject terminal controls or forge report lines."""

import unittest

from devpilot.cli import _human


class TestLogTerminalSafetyTests(unittest.TestCase):
    def test_test_logs_escape_controls_and_prefix_every_line(self):
        output = _human('test', {
            'executed': True,
            'commands': [{
                'ecosystem': 'Python', 'argv': ['python', '-m', 'unittest'],
                'reason': 'unit tests',
                'result': {
                    'exit_code': 1,
                    'stdout': 'begin\nTests: passed\x1b[2J\nplain café',
                    'stderr': 'failure\r\n\u202efake',
                    'error': 'timed out\x1b[31m',
                },
            }],
        })
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn('    stdout | Tests: passed\\x1b[2J', output)
        self.assertIn('    stderr | \\u202efake', output)
        self.assertIn('    stdout | plain café', output)
        self.assertIn('    Error: timed out\\x1b[31m', output)
        self.assertEqual(output.count('\nTests:'), 0)

    def test_untrusted_command_metadata_and_skip_reasons_are_escaped(self):
        output = _human('test', {
            'executed': False,
            'commands': [{
                'ecosystem': 'Python',
                'argv': ['python', 'unsafe\n--script'],
                'reason': 'bad\x1b[31m',
                'skipped_reason': 'untrusted\u202e',
            }],
        })
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn(r'unsafe\x0a--script', output)
        self.assertIn(r'bad\x1b[31m', output)
        self.assertIn(r'untrusted\u202e', output)

    def test_empty_and_multiline_logs_remain_readable(self):
        output = _human('test', {
            'executed': True,
            'commands': [{
                'ecosystem': 'Go', 'argv': ['go', 'test', './...'],
                'reason': 'go.mod',
                'result': {'exit_code': 0, 'stdout': 'PASS\n\nOK\n', 'stderr': ''},
            }],
        })
        self.assertIn('    stdout | PASS\n    stdout | \n    stdout | OK', output)
        self.assertNotIn('    stderr |', output)


if __name__ == '__main__':
    unittest.main()
