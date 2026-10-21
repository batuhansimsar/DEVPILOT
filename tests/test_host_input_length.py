"""Enforce bounded TCP/TLS input before host scans, IDNA and socket activity."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check
from devpilot.tlscheck import MAX_TLS_HOST_LENGTH, _tls_dial_host, tls_check


class HostInputLengthTests(unittest.TestCase):
    def test_oversized_ascii_and_unicode_hosts_never_dial(self):
        for host in (
            'private-host-' + 'a' * MAX_TLS_HOST_LENGTH,
            'é' * (MAX_TLS_HOST_LENGTH + 1),
            '[' + 'a' * MAX_TLS_HOST_LENGTH + ']',
        ):
            for probe in (tcp_check, tls_check):
                with self.subTest(probe=probe.__name__, kind=host[:1]):
                    with patch('socket.create_connection') as connect:
                        with self.assertRaises(ValueError) as caught:
                            probe(host, 443, 1)
                        self.assertEqual(
                            str(caught.exception),
                            f'host exceeds {MAX_TLS_HOST_LENGTH}-character limit',
                        )
                        self.assertNotIn('private-host-', str(caught.exception))
                        connect.assert_not_called()

    def test_direct_parser_uses_same_limit(self):
        with self.assertRaisesRegex(ValueError, 'host exceeds'):
            _tls_dial_host('a' * (MAX_TLS_HOST_LENGTH + 1))

    def test_normal_hosts_still_reach_socket_layer(self):
        for probe in (tcp_check, tls_check):
            with self.subTest(probe=probe.__name__):
                with patch('socket.create_connection', side_effect=ConnectionRefusedError('closed')) as connect:
                    result = probe('example.org', 443, 1)
                self.assertFalse(result['reachable'])
                connect.assert_called_once_with(('example.org', 443), timeout=1)


if __name__ == '__main__':
    unittest.main()
