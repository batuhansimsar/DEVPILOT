"""Canonical rooted IPv4 hosts must remain distinct from legacy numeric aliases."""

import unittest
from unittest.mock import patch

from devpilot.http_url_validation import validate_dns_hostname_labels


class NumericRootDotTests(unittest.TestCase):
    def test_canonical_ipv4_with_terminal_root_dot_is_allowed(self):
        for hostname in (b'127.0.0.1.', b'192.0.2.10.', b'255.255.255.255.'):
            with self.subTest(hostname=hostname):
                validate_dns_hostname_labels(hostname)

    def test_legacy_numeric_aliases_with_root_dot_still_rejected(self):
        for hostname in (
            b'127.1.', b'127.0.0.01.', b'0177.0.0.1.',
            b'0x7f.0.0.1.', b'256.0.0.1.', b'4294967295.',
        ):
            with self.subTest(hostname=hostname):
                with self.assertRaisesRegex(ValueError, 'ambiguous IPv4') as error:
                    validate_dns_hostname_labels(hostname)
                self.assertNotIn(hostname.decode('ascii'), str(error.exception))

    def test_http_check_passes_rooted_canonical_host_to_transport(self):
        from devpilot.httpcheck import http_check

        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://127.0.0.1./health')
        self.assertTrue(result['healthy'])
        opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
