"""Audit failures must not inject control characters into terminal output."""

import json
import unittest

from devpilot.cli import _human


class AuditErrorTerminalSafetyTests(unittest.TestCase):
    def test_ansi_bidi_and_line_breaks_are_escaped(self):
        error = 'Git failure: \\x1b[31m\\n\\u202eoverride\\r'
        rendered = _human('audit', {'error': error})
        self.assertEqual(rendered, r'Audit unavailable: Git failure: \\x1b[31m\\x0a\\u202eoverride\\x0d')
        self.assertNotIn('\\x1b', rendered)
        self.assertNotIn('\\u202e', rendered)
        self.assertNotIn('\\n', rendered)
        self.assertNotIn('\\r', rendered)
        # Human output must be safe without changing the machine-readable data.
        self.assertEqual(json.loads(json.dumps({'error': error}))['error'], error)

    def test_normal_error_remains_readable(self):
        self.assertEqual(_human('audit', {'error': 'Git unavailable'}),
                         'Audit unavailable: Git unavailable')


if __name__ == '__main__':
    unittest.main()
