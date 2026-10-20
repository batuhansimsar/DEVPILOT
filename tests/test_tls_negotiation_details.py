"""Verified TLS probes return actionable, JSON-safe protocol metadata."""

import json
import ssl
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSNegotiationDetailsTests(unittest.TestCase):
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_verified_handshake_includes_negotiated_protocol_and_cipher(self, connect, make_context):
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}
        secured.version.return_value = 'TLSv1.3'
        secured.cipher.return_value = ('TLS_AES_256_GCM_SHA384', 'TLSv1.3', 256)

        result = tls_check('example.com', 443, 1)

        self.assertTrue(result['tls_valid'])
        self.assertEqual(result['tls_version'], 'TLSv1.3')
        self.assertEqual(result['tls_cipher'], 'TLS_AES_256_GCM_SHA384')
        self.assertEqual(result['tls_cipher_bits'], 256)
        self.assertEqual(json.loads(json.dumps(result))['tls_cipher_bits'], 256)

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_unavailable_or_mocked_metadata_not_reported(self, connect, make_context):
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}
        # MagicMock return values should not leak into JSON results.
        secured.cipher.return_value = ('TLS_AES_256_GCM_SHA384', 'TLSv1.3', True)

        result = tls_check('example.com', 443, 1)

        self.assertTrue(result['tls_valid'])
        self.assertNotIn('tls_version', result)
        self.assertEqual(result['tls_cipher'], 'TLS_AES_256_GCM_SHA384')
        self.assertNotIn('tls_cipher_bits', result)
        json.dumps(result)

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_certificate_failure_never_reports_verified_metadata(self, connect, make_context):
        make_context.return_value.wrap_socket.side_effect = ssl.SSLCertVerificationError('untrusted')

        result = tls_check('example.com', 443, 1)

        self.assertFalse(result['tls_valid'])
        self.assertTrue(result['tcp_reachable'])
        self.assertNotIn('tls_version', result)
        self.assertNotIn('tls_cipher', result)
        self.assertNotIn('tls_cipher_bits', result)


if __name__ == '__main__':
    unittest.main()
