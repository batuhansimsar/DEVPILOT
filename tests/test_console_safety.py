"""Regression tests for untrusted filename rendering in human-readable reports."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from devpilot.console import escape_terminal
from devpilot.cli import _human
from devpilot.secret_audit import main as secret_audit_main


class ConsoleSafetyTests(unittest.TestCase):
    def setUp(self):
        self.suspicious = 'nested/.env.\x1b[31m\n\u202e'
        self.escaped = r'nested/.env.\x1b[31m\x0a\u202e'

    def test_escape_controls_without_mangling_unicode_filenames(self):
        self.assertEqual(escape_terminal(self.suspicious), self.escaped)
        self.assertEqual(escape_terminal('café/şifre.pem'), 'café/şifre.pem')
        self.assertEqual(escape_terminal(chr(0xE0001)), r'\U000e0001')

    def test_main_audit_report_cannot_print_terminal_controls(self):
        report = {'tracked_files': 1, 'candidates': [self.suspicious], 'truncated': False}
        output = _human('audit', report)
        self.assertIn(self.escaped, output)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\n\u202e', output)

    def test_doctor_warnings_cannot_print_terminal_controls(self):
        report = {
            'path': '.', 'project_types': [], 'tools': [], 'environment': {},
            'warnings': ['Tracked secret: ' + self.suspicious], 'ok': False,
        }
        output = _human('doctor', report)
        self.assertIn(self.escaped, output)
        self.assertNotIn('\x1b', output)

    def test_secret_audit_human_escapes_but_json_preserves_paths(self):
        report = {
            'path': '.', 'tracked_files_checked': 1, 'ok': False,
            'findings': [{'path': self.suspicious, 'category': 'environment file'}],
            'note': 'Filenames only',
        }
        with patch('devpilot.secret_audit.audit', return_value=report):
            human = io.StringIO()
            with contextlib.redirect_stdout(human):
                self.assertEqual(secret_audit_main(['.']), 1)
            self.assertIn(r'\u001b', human.getvalue())
            self.assertNotIn('\x1b', human.getvalue())
            machine = io.StringIO()
            with contextlib.redirect_stdout(machine):
                self.assertEqual(secret_audit_main(['.', '--json']), 1)
            self.assertEqual(json.loads(machine.getvalue())['findings'][0]['path'], self.suspicious)


if __name__ == '__main__':
    unittest.main()
