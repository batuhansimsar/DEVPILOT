"""IPv6 scope IDs choose the network interface, not the TLS identity."""

import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSIPv6ScopeTests(unittest.TestCase):
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_ipv6_scope_is_preserved_for_dial_but_removed_for_tls(self, connect, context):
        secured = context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}

        for host in ('fe80::1%eth0', '[fe80::1%eth0]'):
            with self.subTest(host=host):
                connect.reset_mock()
                context.return_value.wrap_socket.reset_mock()
                result = tls_check(host, 443, 2)

                connect.assert_called_once_with(('fe80::1%eth0', 443), timeout=2)
                context.return_value.wrap_socket.assert_called_once_with(
                    connect.return_value, server_hostname='fe80::1',
                )
                self.assertTrue(result['tls_valid'])
                self.assertEqual(result['host'], host)


if __name__ == '__main__':
    unittest.main()
