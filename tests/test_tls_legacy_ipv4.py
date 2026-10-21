"""TLS hostname validation must reject ambiguous IPv4 spellings before connecting."""

import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check


class TLSLegacyIPv4Tests(unittest.TestCase):
    def test_noncanonical_ipv4_spellings_never_dial(self):
        candidates = (
            '127.1', '127.0.1', '0177.0.0.1',
            '0x7f000001', '2130706433', '0X7f.0.0.1',
            '127.1.', '0x7f000001.',
        )
        with patch('devpilot.tlscheck.socket.create_connection') as dial:
            for host in candidates:
                with self.subTest(host=host), self.assertRaisesRegex(
                    ValueError, 'host contains an invalid IDNA hostname'
                ):
                    tls_check(host, 443, 1)
            dial.assert_not_called()

    def test_ordinary_dns_and_canonical_ip_still_dial(self):
        candidates = (
            'example.org', 'api123.example.org', 'example.org.',
            '127.0.0.1', '::1',
        )
        with patch('devpilot.tlscheck.socket.create_connection',
                   side_effect=ConnectionRefusedError('closed')) as dial:
            for host in candidates:
                with self.subTest(host=host):
                    self.assertFalse(tls_check(host, 443, 1)['reachable'])
            self.assertEqual(
                [call.args[0][0] for call in dial.call_args_list],
                list(candidates),
            )

    def test_invalid_hostname_errors_do_not_echo_sensitive_input(self):
        with patch('devpilot.tlscheck.socket.create_connection') as dial:
            with self.assertRaises(ValueError) as caught:
                tls_check('secret-prefix.127.1..', 443, 1)
            self.assertNotIn('secret-prefix', str(caught.exception))
            dial.assert_not_called()


if __name__ == '__main__':
    unittest.main()
