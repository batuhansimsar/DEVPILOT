"""TLS probes reject invalid API values before opening any socket."""

import math
import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSInputTypeTests(unittest.TestCase):
    def test_invalid_host_values_are_value_errors(self):
        for host in (None, 123, b'example.org', '', 'bad\x00host', 'bad host'):
            with self.subTest(host=host), patch('devpilot.tlscheck.socket.create_connection') as connect:
                with self.assertRaisesRegex(ValueError, 'host must be'):
                    tls_check(host, 443, 1)
                connect.assert_not_called()

    def test_non_integer_ports_are_rejected(self):
        for port in (True, False, 443.0, '443', None, 0, 65536):
            with self.subTest(port=port), patch('devpilot.tlscheck.socket.create_connection') as connect:
                with self.assertRaisesRegex(ValueError, 'port must be'):
                    tls_check('localhost', port, 1)
                connect.assert_not_called()

    def test_invalid_timeout_types_and_nonfinite_values_are_rejected(self):
        for timeout in (True, False, None, '2', object(), math.nan, math.inf, -math.inf, 0, 30.1):
            with self.subTest(timeout=timeout), patch('devpilot.tlscheck.socket.create_connection') as connect:
                with self.assertRaisesRegex(ValueError, 'timeout must be'):
                    tls_check('localhost', 443, timeout)
                connect.assert_not_called()

    def test_valid_integer_and_float_timeouts_reach_connection(self):
        with patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('closed')) as connect:
            result = tls_check('localhost', 443, 1)
            self.assertFalse(result['tcp_reachable'])
            connect.assert_called_once_with(('localhost', 443), timeout=1)
        with patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('closed')) as connect:
            result = tls_check('localhost', 443, 0.5)
            self.assertFalse(result['reachable'])
            connect.assert_called_once_with(('localhost', 443), timeout=0.5)


if __name__ == '__main__':
    unittest.main()
