"""TLS checks retain a fully qualified DNS dial target but verify its canonical name."""

import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSRootDotIntegrationTests(unittest.TestCase):
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_trailing_root_dot_is_kept_for_tcp_but_removed_for_tls(self, connect, make_context):
        socket = MagicMock()
        connect.return_value = socket
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}

        result = tls_check('example.org.', 443, 2)

        connect.assert_called_once_with(('example.org.', 443), timeout=2)
        make_context.return_value.wrap_socket.assert_called_once_with(
            socket, server_hostname='example.org',
        )
        self.assertTrue(result['tls_valid'])
        self.assertEqual(result['host'], 'example.org.')

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_ordinary_dns_hostname_does_not_change(self, connect, make_context):
        socket = connect.return_value
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}

        result = tls_check('example.org', 443, 2)

        make_context.return_value.wrap_socket.assert_called_once_with(
            socket, server_hostname='example.org',
        )
        self.assertTrue(result['tls_valid'])


if __name__ == '__main__':
    unittest.main()
