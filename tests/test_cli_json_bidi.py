"""Prevent terminal direction-control spoofing in CLI JSON diagnostics."""

import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from devpilot.cli import main


class CLIJSONSafetyTests(unittest.TestCase):
    def test_json_audit_escapes_direction_controls(self):
        hostile = 'secrets/\u202efake.txt\u2066.key'
        with tempfile.TemporaryDirectory() as directory:
            report = {'path': directory, 'tracked_files': 1,
                      'candidates': [hostile], 'truncated': False}
            output = io.StringIO()
            with patch('devpilot.cli.audit_tracked_files', return_value=report):
                with contextlib.redirect_stdout(output):
                    status = main(['audit', '--path', directory, '--json'])
        data = output.getvalue()
        self.assertEqual(status, 1)
        self.assertNotIn('\u202e', data)
        self.assertNotIn('\u2066', data)
        self.assertIn('\\u202e', data)
        self.assertIn('\\u2066', data)
        self.assertEqual(json.loads(data), report)


if __name__ == '__main__':
    unittest.main()
