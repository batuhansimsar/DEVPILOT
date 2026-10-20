"""Malformed optional certificate metadata cannot change TLS verification status."""

import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSMalformedExpiryTests(unittest.TestCase):
    def test_malformed_expiry_does_not_mark_verified_tls_unhealthy(self):
        for expiry in ('not-a-date', 12345, ['bad'], 'Dec 99 99:99:99 9999 GMT'):
            with self.subTest(expiry=expiry), \
                    patch('devpilot.tlscheck.socket.create_connection') as connect, \
                    patch('devpilot.tlscheck.ssl.create_default_context') as context:
                connect.return_value = MagicMock()
                secured = MagicMock()
                secured.__enter__.return_value = secured
                secured.getpeercert.return_value = {'notAfter': expiry}
                context.return_value.wrap_socket.return_value = secured
                result = tls_check('example.org', 443, 2)
                self.assertTrue(result['reachable'])
                self.assertTrue(result['tls_valid'])
                self.assertTrue(result['tcp_reachable'])
                self.assertNotIn('error', result)
                self.assertNotIn('expires_at', result)
                self.assertNotIn('expires_in_days', result)
                self.assertNotIn('expires_soon', result)

    @patch('devpilot.tlscheck.socket.create_connection')
    @patch('devpilot.tlscheck.ssl.create_default_context')
    def test_unexpected_certificate_shape_does_not_crash(self, context, connect):
        connect.return_value = MagicMock()
        secured = MagicMock()
        secured.__enter__.return_value = secured
        secured.getpeercert.return_value = ['not-a-certificate-dict']
        context.return_value.wrap_socket.return_value = secured
        result = tls_check('example.org', 443, 2)
        self.assertTrue(result['tls_valid'])
        self.assertNotIn('error', result)
        self.assertNotIn('expires_at', result)


if __name__ == '__main__':
    unittest.main()
