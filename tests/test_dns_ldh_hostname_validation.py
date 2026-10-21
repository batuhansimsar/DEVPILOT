"""Only DNS host-label characters may reach TCP or TLS socket creation."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check
from devpilot.tlscheck import _tls_dial_host, tls_check


class DNSLDHHostnameValidationTests(unittest.TestCase):
    def test_invalid_ascii_label_characters_are_rejected_before_dial(self):
        invalid = (
            'bad_name.example', 'bad+name.example', 'bad%2ename.example',
            'bad!name.example', 'bad=name.example', 'bad*name.example',
            'bad,name.example', 'bad~name.example', 'bad|name.example',
        )
        for probe, target in (
            (tcp_check, 'devpilot.core.socket.create_connection'),
            (tls_check, 'devpilot.tlscheck.socket.create_connection'),
        ):
            with patch(target) as connect:
                for host in invalid:
                    with self.subTest(probe=probe.__name__, host=host):
                        with self.assertRaisesRegex(ValueError, 'invalid IDNA hostname') as raised:
                            probe(host, 443, 1)
                        self.assertNotIn(host, str(raised.exception))
                connect.assert_not_called()

    def test_valid_alphanumeric_hyphen_and_unicode_labels_remain_supported(self):
        for host in ('A-1.example', 'localhost', '127.0.0.1',
                     'bücher.example', 'example.org.', 'x' * 63 + '.example'):
            with self.subTest(host=host):
                self.assertEqual(_tls_dial_host(host), host)


if __name__ == '__main__':
    unittest.main()
