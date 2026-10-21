"""Malformed IDNA A-labels must fail before a health probe can resolve them."""

import unittest

from devpilot.http_url_validation import validate_dns_hostname_labels


class IDNAAliasValidationTests(unittest.TestCase):
    def test_rejects_invalid_alabels_without_exposing_hostnames(self):
        for host in (b'xn--a.example', b'xn--abc.example', b'xn--0.example',
                     b'XN--A.example', b'api.xn--a.'):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, 'invalid IDNA label') as caught:
                validate_dns_hostname_labels(host)
            self.assertNotIn(host.decode('ascii'), str(caught.exception))

    def test_accepts_valid_alabels_ascii_and_ipv4(self):
        for host in (b'xn--bcher-kva.example', b'XN--BCHER-KVA.example.',
                     b'api.example.org', b'127.0.0.1', b'localhost'):
            with self.subTest(host=host):
                validate_dns_hostname_labels(host)

    def test_invalid_alabel_cannot_hide_after_valid_label(self):
        with self.assertRaisesRegex(ValueError, 'invalid IDNA label'):
            validate_dns_hostname_labels(b'valid.example.xn--abc')


if __name__ == '__main__':
    unittest.main()
