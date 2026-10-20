"""TLS host normalization must not silently reinterpret user-supplied URLs."""

import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSHostValidationTests(unittest.TestCase):
    def test_url_and_embedded_port_inputs_are_rejected_without_network(self):
        invalid = (
            'https://example.org', 'example.org:443', 'example.org/path',
            'example.org?query=1', 'example.org#fragment',
            'user@example.org', r'example.org\\path',
            '[::1]:443', '[example.org]', '[127.0.0.1]',
            '::1]', '[::1', '[::1]]', '[::1]:443',
        )
        with patch('devpilot.tlscheck.socket.create_connection') as connect:
            for host in invalid:
                with self.subTest(host=host), self.assertRaises(ValueError):
                    tls_check(host, 443, 1)
            connect.assert_not_called()

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_bracketed_ipv6_is_normalized_for_dial_and_tls(self, connect, make_context):
        sock = connect.return_value
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}
        result = tls_check('[::1]', 443, 1)
        connect.assert_called_once_with(('::1', 443), timeout=1)
        make_context.return_value.wrap_socket.assert_called_once_with(sock, server_hostname='::1')
        self.assertEqual(result['host'], '[::1]')
        self.assertTrue(result['tls_valid'])

    @patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('closed'))
    def test_valid_ipv6_and_hostname_reach_socket_layer(self, connect):
        for host in ('::1', 'example.org', '127.0.0.1'):
            with self.subTest(host=host):
                result = tls_check(host, 443, 1)
                self.assertFalse(result['reachable'])
        self.assertEqual([call.args[0][0] for call in connect.call_args_list],
                         ['::1', 'example.org', '127.0.0.1'])


if __name__ == '__main__':
    unittest.main()
