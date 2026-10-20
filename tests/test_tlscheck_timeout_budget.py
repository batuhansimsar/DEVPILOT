"""TLS negotiation shares the same timeout budget as TCP setup."""

import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSCheckTimeoutBudgetTests(unittest.TestCase):
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[100.0, 100.4, 100.5, 100.5, 100.6])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_handshake_uses_remaining_timeout(self, connect, make_context, clock):
        sock = MagicMock()
        connect.return_value = sock
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = {}
        make_context.return_value.wrap_socket.return_value = secured

        result = tls_check('example.com', 443, 2)

        connect.assert_called_once_with(('example.com', 443), timeout=2)
        sock.settimeout.assert_called_once()
        self.assertAlmostEqual(sock.settimeout.call_args.args[0], 1.5)
        self.assertTrue(result['tls_valid'])
        self.assertEqual(result['tls_handshake_ms'], 100.0)

    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[100.0, 100.8, 101.1])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_expired_budget_skips_handshake_and_closes_tcp(self, connect, make_context, clock):
        sock = MagicMock()
        connect.return_value = sock

        result = tls_check('example.com', 443, 1)

        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertFalse(result['reachable'])
        self.assertIn('timeout', result['error'])
        sock.settimeout.assert_not_called()
        make_context.return_value.wrap_socket.assert_not_called()
        sock.__exit__.assert_called_once()
        self.assertNotIn('tls_handshake_ms', result)

    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[100.0, 100.6, 100.9, 100.9, 101.0])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_context_setup_time_counts_against_budget(self, connect, make_context, clock):
        connect.return_value = MagicMock()
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = {}
        make_context.return_value.wrap_socket.return_value = secured

        result = tls_check('example.com', 443, 1)

        self.assertAlmostEqual(connect.return_value.settimeout.call_args.args[0], 0.1)
        self.assertTrue(result['reachable'])


if __name__ == '__main__':
    unittest.main()
