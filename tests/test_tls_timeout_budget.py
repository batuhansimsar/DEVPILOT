"""TLS handshakes share the advertised timeout with the TCP connection."""

import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSTimeoutBudgetTests(unittest.TestCase):
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 10.75, 10.80, 10.90])
    def test_handshake_receives_only_remaining_time(self, clock, connect, make_context):
        sock = MagicMock()
        connect.return_value = sock
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}

        result = tls_check('example.org', 443, 2.0)

        connect.assert_called_once_with(('example.org', 443), timeout=2.0)
        sock.settimeout.assert_called_once_with(1.25)
        self.assertTrue(result['tls_valid'])
        self.assertEqual(result['tcp_latency_ms'], 750.0)
        self.assertEqual(result['tls_handshake_ms'], 100.0)

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 12.01])
    def test_exhausted_tcp_budget_skips_handshake_and_closes_socket(self, clock, connect, make_context):
        sock = MagicMock()
        connect.return_value = sock

        result = tls_check('example.org', 443, 2.0)

        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertIn('timeout budget', result['error'])
        self.assertNotIn('tls_handshake_ms', result)
        make_context.assert_not_called()
        sock.__exit__.assert_called_once()

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 10.2, 10.3, 10.6])
    def test_failed_handshake_is_bounded_and_reported(self, clock, connect, make_context):
        sock = MagicMock()
        connect.return_value = sock
        make_context.return_value.wrap_socket.side_effect = TimeoutError('handshake timed out')

        result = tls_check('example.org', 443, 1.0)

        sock.settimeout.assert_called_once()
        self.assertAlmostEqual(sock.settimeout.call_args.args[0], 0.8)
        self.assertFalse(result['tls_valid'])
        self.assertEqual(result['tls_handshake_ms'], 300.0)
        self.assertIn('handshake timed out', result['error'])


if __name__ == '__main__':
    unittest.main()
