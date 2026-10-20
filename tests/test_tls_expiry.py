"""TLS expiry metadata tests run offline with a mocked TLS session."""

import datetime
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSExpiryTests(unittest.TestCase):
    def probe(self, expiry):
        with patch('devpilot.tlscheck.socket.create_connection') as connect, \
                patch('devpilot.tlscheck.ssl.create_default_context') as make_context:
            socket = MagicMock()
            connect.return_value = socket
            secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
            secured.getpeercert.return_value = {'notAfter': expiry} if expiry else {}
            result = tls_check('example.org', 443, 2)
            make_context.return_value.wrap_socket.assert_called_once_with(socket, server_hostname='example.org')
            return result

    def expiry(self, days):
        return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).strftime('%b %d %H:%M:%S %Y GMT')

    def test_expiring_certificate_is_reported(self):
        result = self.probe(self.expiry(10))
        self.assertTrue(result['tls_valid'])
        self.assertTrue(result['reachable'])
        self.assertTrue(result['expires_soon'])
        self.assertGreaterEqual(result['expires_in_days'], 9)
        self.assertLessEqual(result['expires_in_days'], 10)
        self.assertTrue(result['expires_at'].endswith('Z'))

    def test_long_lived_certificate_has_no_warning(self):
        result = self.probe(self.expiry(60))
        self.assertFalse(result['expires_soon'])
        self.assertGreaterEqual(result['expires_in_days'], 59)

    def test_missing_certificate_expiry_does_not_invent_remaining_days(self):
        result = self.probe(None)
        self.assertTrue(result['tls_valid'])
        self.assertNotIn('expires_in_days', result)
        self.assertNotIn('expires_soon', result)


if __name__ == '__main__':
    unittest.main()
