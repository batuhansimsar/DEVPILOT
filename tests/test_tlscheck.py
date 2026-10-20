"""No external network required: TLS checks use socket/SSL mocks."""

import contextlib
import io
import json
import ssl
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check
from devpilot.cli import main


class TLSCheckTests(unittest.TestCase):
    def test_invalid_port(self):
        with self.assertRaises(ValueError):
            tls_check('localhost', 0, 1)
        with self.assertRaises(ValueError):
            tls_check('localhost', 65536, 1)

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_trusted_handshake_and_expiration(self, connect, make_context):
        sock = MagicMock()
        connect.return_value = sock
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = {'notAfter': 'Jun  1 12:00:00 2030 GMT'}
        make_context.return_value.wrap_socket.return_value = secured
        result = tls_check('example.com', 443, 2)
        connect.assert_called_once_with(('example.com', 443), timeout=2)
        make_context.return_value.wrap_socket.assert_called_once_with(sock, server_hostname='example.com')
        self.assertTrue(result['reachable'])
        self.assertTrue(result['tcp_reachable'])
        self.assertTrue(result['tls_valid'])
        self.assertEqual(result['expires_at'], '2030-06-01T12:00:00Z')

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_invalid_certificate_distinguished_from_tcp_failure(self, connect, make_context):
        connect.return_value = MagicMock()
        make_context.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError('certificate verify failed')
        result = tls_check('localhost', 443, 1)
        self.assertFalse(result['reachable'])
        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertIn('certificate', result['error'])

    @patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('refused'))
    def test_tcp_connection_failure(self, connect):
        result = tls_check('localhost', 443, 1)
        self.assertFalse(result['reachable'])
        self.assertFalse(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertEqual(result['error'], 'refused')

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_no_certificate_expiry_is_ok(self, connect, make_context):
        connect.return_value = MagicMock()
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = {}
        make_context.return_value.wrap_socket.return_value = secured
        result = tls_check('localhost', 443, 1)
        self.assertTrue(result['reachable'])
        self.assertNotIn('expires_at', result)

    @patch('devpilot.cli.tls_check', return_value={
        'host': 'localhost', 'port': 443, 'reachable': True,
        'tcp_reachable': True, 'tls_valid': True, 'expires_at': '2030-06-01T12:00:00Z',
    })
    def test_cli_tls_json_dispatch(self, check):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(['check', 'localhost', '443', '--tls', '--json'])
        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(output.getvalue())['tls_valid'])
        check.assert_called_once_with('localhost', 443, 3)


    @patch('devpilot.tlscheck.time.monotonic', side_effect=[10.0, 10.1234])
    @patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('refused'))
    def test_failed_tcp_records_latency(self, connect, clock):
        result = tls_check('localhost', 443, 2)
        self.assertEqual(result['latency_ms'], 123.4)
        self.assertFalse(result['tcp_reachable'])

    @patch('devpilot.tlscheck.time.monotonic', side_effect=[10.0, 10.1234])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_verified_tls_records_latency(self, connect, context, clock):
        connect.return_value = MagicMock()
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = {}
        context.return_value.wrap_socket.return_value = secured
        result = tls_check('example.com', 443, 2)
        self.assertEqual(result['latency_ms'], 123.4)
        self.assertTrue(result['tls_valid'])

    @patch('devpilot.tlscheck.time.monotonic', side_effect=[10.0, 10.1234])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_invalid_certificate_records_latency(self, connect, context, clock):
        connect.return_value = MagicMock()
        context.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError('invalid cert')
        result = tls_check('example.com', 443, 2)
        self.assertEqual(result['latency_ms'], 123.4)
        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])


if __name__ == '__main__':
    unittest.main()
