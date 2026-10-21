"""Legacy numeric host aliases must not silently redirect HTTP probes."""

import unittest
from unittest.mock import patch

from devpilot.http_url_validation import validate_dns_hostname_labels


class AmbiguousIPv4Tests(unittest.TestCase):
    def test_rejects_legacy_ipv4_aliases_without_network_resolution(self):
        for host in (b'127.1', b'127.0.1', b'2130706433',
                     b'0177.0.0.1', b'0x7f000001',
                     b'01.2.3.4', b'127.0.0.999'):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, 'ambiguous IPv4') as raised:
                    validate_dns_hostname_labels(host)
                self.assertNotIn(host.decode('ascii'), str(raised.exception))

    def test_allows_canonical_ipv4_and_regular_dns_names(self):
        for host in (b'127.0.0.1', b'127.0.0.1.', b'0.0.0.0', b'255.255.255.255',
                     b'example.org', b'example.org.', b'a1.b2',
                     b'xn--bcher-kva.example'):
            with self.subTest(host=host):
                validate_dns_hostname_labels(host)

    def test_http_probe_rejects_legacy_hosts_before_transport(self):
        from devpilot.httpcheck import http_check
        for host in ('127.1', '2130706433', '0177.0.0.1', '0x7f000001'):
            with self.subTest(host=host), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'ambiguous IPv4'):
                    http_check(f'http://{host}/health?token=private-value')
                opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
