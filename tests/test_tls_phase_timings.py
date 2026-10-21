"""Stable, network-free regression tests for TCP vs. TLS timing diagnostics."""

import ssl
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSPhaseTimingTests(unittest.TestCase):
    @patch('devpilot.tlscheck.time.monotonic', side_effect=[5.0, 5.3])
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 10.05, 10.06, 10.06, 10.26])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_splits_successful_connection_and_handshake(self, connect, make_context, clock, total_clock):
        socket = MagicMock()
        connect.return_value = socket
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}

        result = tls_check('example.com', 443, 2)

        self.assertEqual(result['tcp_latency_ms'], 50.0)
        self.assertEqual(result['tls_handshake_ms'], 200.0)
        self.assertEqual(result['latency_ms'], 300.0)
        self.assertTrue(result['tls_valid'])
        make_context.return_value.wrap_socket.assert_called_once_with(socket, server_hostname='example.com')

    @patch('devpilot.tlscheck.time.monotonic', side_effect=[5.0, 5.1])
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 10.07])
    @patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('refused'))
    def test_tcp_failure_does_not_claim_tls_handshake(self, connect, clock, total_clock):
        result = tls_check('example.com', 443, 2)
        self.assertEqual(result['tcp_latency_ms'], 70.0)
        self.assertNotIn('tls_handshake_ms', result)
        self.assertEqual(result['latency_ms'], 100.0)
        self.assertFalse(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])

    @patch('devpilot.tlscheck.time.monotonic', side_effect=[5.0, 5.2])
    @patch('devpilot.tlscheck.time.perf_counter', side_effect=[10.0, 10.01, 10.02, 10.02, 10.17])
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_tls_failure_still_reports_handshake_duration(self, connect, make_context, clock, total_clock):
        connect.return_value = MagicMock()
        make_context.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError('certificate rejected')

        result = tls_check('example.com', 443, 2)

        self.assertEqual(result['tcp_latency_ms'], 10.0)
        self.assertEqual(result['tls_handshake_ms'], 150.0)
        self.assertEqual(result['latency_ms'], 200.0)
        self.assertTrue(result['tcp_reachable'])
        self.assertFalse(result['tls_valid'])
        self.assertFalse(result['reachable'])


if __name__ == '__main__':
    unittest.main()
