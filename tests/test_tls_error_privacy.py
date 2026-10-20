"""TLS diagnostics must not echo exception strings provided by the network or OS."""

import errno
import json
import ssl
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSErrorPrivacyTests(unittest.TestCase):
    def test_tcp_failure_redacts_private_exception_message(self):
        secret = 'private-password\n\x1b[31m'
        with patch('devpilot.tlscheck.socket.create_connection',
                   side_effect=OSError(errno.EHOSTUNREACH, secret)):
            result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'EHOSTUNREACH')
        self.assertNotIn('private-password', json.dumps(result))
        self.assertFalse(result['tcp_reachable'])

    def test_tcp_timeout_reports_tcp_phase(self):
        with patch('devpilot.tlscheck.socket.create_connection',
                   side_effect=TimeoutError('private socket details')):
            result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'TCP connection timed out')
        self.assertNotIn('private socket details', json.dumps(result))
        self.assertNotIn('tls_handshake_ms', result)

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_tls_failure_redacts_private_exception_message(self, connect, context):
        connect.return_value = MagicMock()
        context.return_value.wrap_socket.side_effect = ssl.SSLError('private-token\x1b[2J')
        result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'TLS handshake failed')
        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertNotIn('private-token', json.dumps(result))

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_verification_errors_preserve_safe_actionable_category(self, connect, context):
        connect.return_value = MagicMock()
        context.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError('sensitive subject')
        result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'certificate verification failed')
        self.assertNotIn('sensitive', json.dumps(result))

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_expired_budget_has_stable_timeout_description(self, connect, context):
        connect.return_value = MagicMock()
        with patch('devpilot.tlscheck.time.perf_counter', side_effect=[10, 12, 12.1]):
            result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'TLS handshake timeout budget exhausted before negotiation')
        context.return_value.wrap_socket.assert_not_called()

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_externally_raised_timeout_text_is_redacted(self, connect, context):
        connect.return_value = MagicMock()
        context.return_value.wrap_socket.side_effect = TimeoutError('secret-handshake-detail')
        result = tls_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'TLS handshake timed out')
        self.assertNotIn('secret-handshake-detail', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
