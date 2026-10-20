"""Avoid visually deceptive TLS endpoint labels and unwanted network activity."""

import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSUnicodeHostSafetyTests(unittest.TestCase):
    def test_nonprinting_unicode_hostnames_are_rejected_before_network(self):
        hosts = ('example.org\u202e', 'example.org\u2066', 'example.org\u200d')
        with patch('devpilot.tlscheck.socket.create_connection') as connect:
            for host in hosts:
                with self.subTest(host=repr(host)), self.assertRaisesRegex(ValueError, 'host must be'):
                    tls_check(host, 443, 1)
            connect.assert_not_called()

    def test_normal_hostname_still_reaches_socket_layer(self):
        with patch('devpilot.tlscheck.socket.create_connection', side_effect=ConnectionRefusedError('closed')) as connect:
            report = tls_check('example.org', 443, 1)
        self.assertFalse(report['reachable'])
        connect.assert_called_once_with(('example.org', 443), timeout=1)


if __name__ == '__main__':
    unittest.main()
