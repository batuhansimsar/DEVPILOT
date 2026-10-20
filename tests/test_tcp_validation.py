"""TCP probes reject invalid inputs before any socket connection is opened."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check


class TCPInputValidationTests(unittest.TestCase):
    def test_invalid_endpoint_does_not_open_socket(self):
        with patch('devpilot.core.socket.create_connection') as connect:
            for host, port, timeout in (
                ('', 443, 3),
                ('bad host', 443, 3),
                ('host\nspoof', 443, 3),
                ('host\x1b[31m', 443, 3),
                (None, 443, 3),
                ('example.org', 0, 3),
                ('example.org', 65536, 3),
                ('example.org', True, 3),
                ('example.org', 443, 0),
                ('example.org', 443, 31),
                ('example.org', 443, float('nan')),
                ('example.org', 443, None),
            ):
                with self.subTest(host=host, port=port, timeout=timeout):
                    with self.assertRaises(ValueError):
                        tcp_check(host, port, timeout)
            connect.assert_not_called()

    def test_valid_endpoint_uses_requested_host_and_timeout(self):
        with patch('devpilot.core.socket.create_connection') as connect:
            result = tcp_check('example.org', 443, 2)
        self.assertTrue(result['reachable'])
        self.assertEqual(result['host'], 'example.org')
        connect.assert_called_once_with(('example.org', 443), timeout=2)

    def test_connection_failure_remains_a_health_result(self):
        with patch('devpilot.core.socket.create_connection', side_effect=ConnectionRefusedError('refused')):
            result = tcp_check('example.org', 443, 2)
        self.assertFalse(result['reachable'])
        self.assertIn('refused', result['error'])


if __name__ == '__main__':
    unittest.main()
