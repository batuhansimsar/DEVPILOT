"""Prevent Unicode direction overrides in JSON audit output."""

import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from devpilot.secret_audit import main


class JSONBidiAuditTests(unittest.TestCase):
    def test_json_output_escapes_direction_overrides_without_losing_path(self):
        hostile = 'private/\u202eoverride\u2066.key'
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            with patch('devpilot.secret_audit._tracked_paths',
                       return_value=hostile.encode('utf-8') + b'\0'):
                with contextlib.redirect_stdout(stdout):
                    status = main([directory, '--json'])
        output = stdout.getvalue()
        self.assertEqual(status, 1)
        self.assertNotIn('\u202e', output)
        self.assertNotIn('\u2066', output)
        self.assertIn('\\u202e', output)
        self.assertIn('\\u2066', output)
        data = json.loads(output)
        self.assertEqual(data['findings'][0]['path'], hostile)
        self.assertNotIn('error', data)


if __name__ == '__main__':
    unittest.main()
