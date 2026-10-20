"""Validation failures must not print supplied network identifiers in traceback chains."""

import traceback
import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check
from devpilot.tlscheck import tls_check


class NetworkValidationTracebackPrivacyTests(unittest.TestCase):
    def test_invalid_http_port_does_not_reveal_user_input_in_traceback(self):
        marker = 'PRIVATE_HTTP_PORT_MARKER'
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'invalid port') as caught:
                http_check(f'https://example.org:{marker}/health')
        opener.assert_not_called()
        self.assertNotIn(marker, ''.join(traceback.format_exception(caught.exception)))

    def test_invalid_ipv6_host_does_not_reveal_user_input_in_traceback(self):
        marker = 'PRIVATE_IPV6_HOST_MARKER'
        with patch('devpilot.tlscheck.socket.create_connection') as connection:
            with self.assertRaisesRegex(ValueError, 'invalid IPv6') as caught:
                tls_check(f'{marker}:broken', 443, 1.0)
        connection.assert_not_called()
        self.assertNotIn(marker, ''.join(traceback.format_exception(caught.exception)))

    def test_invalid_bracketed_ipv6_does_not_reveal_input_in_traceback(self):
        marker = 'PRIVATE_BRACKETED_HOST_MARKER'
        with patch('devpilot.tlscheck.socket.create_connection') as connection:
            with self.assertRaisesRegex(ValueError, 'valid IPv6') as caught:
                tls_check(f'[{marker}]', 443, 1.0)
        connection.assert_not_called()
        self.assertNotIn(marker, ''.join(traceback.format_exception(caught.exception)))


if __name__ == '__main__':
    unittest.main()
