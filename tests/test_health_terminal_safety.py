"""HTTP/TCP/TLS human reports must not interpret untrusted terminal controls."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from devpilot.cli import _human, main


class HealthTerminalSafetyTests(unittest.TestCase):
    def setUp(self):
        self.hostile = 'details\x1b[2J\n\u202e'
        self.safe = r'details\x1b[2J\x0a\u202e'

    def assert_safe(self, rendered):
        self.assertIn(self.safe, rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)
        self.assertEqual(rendered.count('\n'), 0)

    def test_tcp_failure_does_not_inject_terminal_controls(self):
        report = {'host': 'example.org', 'port': 443, 'reachable': False,
                  'error': self.hostile}
        self.assert_safe(_human('check', report))

    def test_tls_failure_does_not_inject_terminal_controls(self):
        report = {'host': 'example.org', 'port': 443, 'reachable': False,
                  'tls_valid': False, 'error': self.hostile}
        self.assert_safe(_human('check', report))

    def test_http_failure_does_not_inject_terminal_controls(self):
        report = {'url': 'https://example.org/ready', 'reachable': False,
                  'status': None, 'error': self.hostile}
        self.assert_safe(_human('http', report))

    def test_health_endpoint_and_expiry_metadata_are_escaped(self):
        bad_host = 'host\x1b[31m'
        tls_report = {'host': bad_host, 'port': 443, 'reachable': True,
                      'tls_valid': True, 'expires_at': self.hostile}
        rendered = _human('check', tls_report)
        self.assertIn(r'host\x1b[31m', rendered)
        self.assert_safe(rendered)
        http_report = {'url': 'https://example.org/' + self.hostile,
                       'reachable': True, 'status': 204, 'healthy': True}
        self.assert_safe(_human('http', http_report))

    def test_json_keeps_original_diagnostics(self):
        report = {'url': 'https://example.org/ready', 'method': 'HEAD',
                  'reachable': False, 'status': None, 'healthy': False,
                  'error': self.hostile}
        stream = io.StringIO()
        with patch('devpilot.cli.http_check', return_value=report), contextlib.redirect_stdout(stream):
            code = main(['http', 'https://example.org/ready', '--json'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stream.getvalue())['error'], self.hostile)


if __name__ == '__main__':
    unittest.main()
