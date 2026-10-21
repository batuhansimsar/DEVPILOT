"""Failures in optional TLS metadata cannot contradict verified handshakes."""

import json
import ssl
import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSOptionalMetadataFailureTests(unittest.TestCase):
    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_version_lookup_failure_keeps_verified_handshake(self, connect, make_context):
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}
        secured.version.side_effect = ssl.SSLError('private certificate subject')
        secured.cipher.return_value = ('TLS_AES_128_GCM_SHA256', 'TLSv1.3', 128)

        result = tls_check('example.org', 443, 2)

        self.assertTrue(result['reachable'])
        self.assertTrue(result['tls_valid'])
        self.assertTrue(result['tcp_reachable'])
        self.assertNotIn('error', result)
        self.assertNotIn('tls_version', result)
        self.assertEqual(result['tls_cipher'], 'TLS_AES_128_GCM_SHA256')
        self.assertNotIn('private certificate subject', json.dumps(result))

    @patch('devpilot.tlscheck.ssl.create_default_context')
    @patch('devpilot.tlscheck.socket.create_connection')
    def test_cipher_lookup_failure_preserves_version(self, connect, make_context):
        secured = make_context.return_value.wrap_socket.return_value.__enter__.return_value
        secured.getpeercert.return_value = {}
        secured.version.return_value = 'TLSv1.3'
        secured.cipher.side_effect = OSError('private network details')

        result = tls_check('example.org', 443, 2)

        self.assertTrue(result['reachable'])
        self.assertTrue(result['tls_valid'])
        self.assertNotIn('error', result)
        self.assertEqual(result['tls_version'], 'TLSv1.3')
        self.assertNotIn('tls_cipher', result)
        self.assertNotIn('tls_cipher_bits', result)
        self.assertNotIn('private network details', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
