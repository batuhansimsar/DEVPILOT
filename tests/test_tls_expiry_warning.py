"""Regression tests for actionable TLS certificate renewal warnings."""

import datetime
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSExpirationWarningTests(unittest.TestCase):
    def probe_with_expiry(self, days_until_expiry):
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_until_expiry)
        certificate = {'notAfter': expiry.strftime('%b %d %H:%M:%S %Y GMT')}
        with patch('devpilot.tlscheck.socket.create_connection') as connect, \
             patch('devpilot.tlscheck.ssl.create_default_context') as make_context:
            secured = MagicMock()
            secured.__enter__.return_value = secured
            secured.getpeercert.return_value = certificate
            make_context.return_value.wrap_socket.return_value = secured
            result = tls_check('example.com', 443, 2.0)
        self.assertTrue(result['tls_valid'])
        self.assertTrue(result['reachable'])
        connect.assert_called_once_with(('example.com', 443), timeout=2.0)
        return result

    def test_expiring_soon_warns_but_handshake_remains_healthy(self):
        result = self.probe_with_expiry(7)
        self.assertTrue(result['expires_soon'])
        self.assertIn('expires_at', result)

    def test_long_lived_certificate_has_no_warning(self):
        result = self.probe_with_expiry(90)
        self.assertFalse(result['expires_soon'])

    def test_missing_expiry_is_not_called_expiring_soon(self):
        with patch('devpilot.tlscheck.socket.create_connection'), \
             patch('devpilot.tlscheck.ssl.create_default_context') as make_context:
            secured = MagicMock()
            secured.__enter__.return_value = secured
            secured.getpeercert.return_value = {}
            make_context.return_value.wrap_socket.return_value = secured
            result = tls_check('example.com', 443, 2)
        self.assertNotIn('expires_soon', result)


if __name__ == '__main__':
    unittest.main()
