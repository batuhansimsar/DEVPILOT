"""Malformed IPv6 probe targets must not appear in validation tracebacks."""

import traceback
import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSHostParserPrivacyTests(unittest.TestCase):
    def test_invalid_ipv6_reports_only_safe_error_without_dialing(self):
        for host, expected in (
            ('[private-ipv6-token]', 'bracketed host must be a valid IPv6 address'),
            ('2001:db8::private-ipv6-token', 'host contains an invalid IPv6 address or embedded port'),
        ):
            with self.subTest(host=host), patch('devpilot.tlscheck.socket.create_connection') as dial:
                with self.assertRaises(ValueError) as raised:
                    tls_check(host, 443, 1)
                self.assertEqual(str(raised.exception), expected)
                self.assertIsNone(raised.exception.__cause__)
                self.assertNotIn('private-ipv6-token', ''.join(traceback.format_exception(raised.exception)))
                dial.assert_not_called()

    def test_valid_ipv6_addresses_still_reach_socket_layer(self):
        with patch('devpilot.tlscheck.socket.create_connection',
                   side_effect=ConnectionRefusedError('closed')) as dial:
            for host in ('::1', '[::1]'):
                with self.subTest(host=host):
                    result = tls_check(host, 443, 1)
                    self.assertFalse(result['reachable'])
                    self.assertTrue(result['error'])
            self.assertEqual([call.args[0][0] for call in dial.call_args_list],
                             ['::1', '::1'])


if __name__ == '__main__':
    unittest.main()
