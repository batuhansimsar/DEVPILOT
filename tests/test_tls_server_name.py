"""TLS peer identity must exclude DNS root dots and IPv6 interface zones."""

import unittest
from devpilot.tls_server_name import tls_server_name


class TLSServerNameTests(unittest.TestCase):
    def test_absolute_dns_names_use_same_tls_name_as_relative_form(self):
        for host in ('example.org.', 'sub.example.org.', 'b\u00fccher.example.'):
            with self.subTest(host=host):
                self.assertEqual(tls_server_name(host), host[:-1])

    def test_unqualified_dns_names_and_unscoped_ip_literals_are_unchanged(self):
        for host in ('example.org', 'localhost', '127.0.0.1', '::1'):
            with self.subTest(host=host):
                self.assertEqual(tls_server_name(host), host)

    def test_ipv6_zone_is_not_part_of_certificate_identity(self):
        for host in ('fe80::1%eth0', 'fe80::abcd%12', '::1%lo0'):
            with self.subTest(host=host):
                self.assertEqual(tls_server_name(host), host.partition('%')[0])


if __name__ == '__main__':
    unittest.main()
