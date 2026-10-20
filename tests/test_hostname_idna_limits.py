"""Malformed IDNA hosts must be rejected before opening TCP/TLS sockets."""

import unittest
from unittest.mock import patch

from devpilot.tlscheck import _tls_dial_host, tls_check
from devpilot.core import tcp_check


class HostnameIDNALimitTests(unittest.TestCase):
    def test_overlong_ascii_and_unicode_labels_rejected_before_dial(self):
        for host in ('a' * 64 + '.example', '\u00e9' * 65 + '.example'):
            for probe, target in (
                (tls_check, 'devpilot.tlscheck.socket.create_connection'),
                (tcp_check, 'devpilot.core.socket.create_connection'),
            ):
                with self.subTest(host=host[:10], probe=probe.__name__), patch(target) as connect:
                    with self.assertRaisesRegex(ValueError, 'invalid IDNA hostname'):
                        probe(host, 443, 1)
                    connect.assert_not_called()

    def test_valid_unicode_hostname_keeps_original_dial_target(self):
        host = 'b\u00fccher.example'
        self.assertEqual(_tls_dial_host(host), host)
        with patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('closed')) as connect:
            result = tls_check(host, 443, 1)
        self.assertFalse(result['reachable'])
        connect.assert_called_once_with((host, 443), timeout=1)

    def test_bracketed_ipv6_still_normalizes(self):
        self.assertEqual(_tls_dial_host('[::1]'), '::1')


if __name__ == '__main__':
    unittest.main()
