"""A DNS root dot must not change the TLS certificate identity."""

import unittest
from devpilot.tls_server_name import tls_server_name


class TLSServerNameTests(unittest.TestCase):
    def test_absolute_dns_names_use_same_tls_name_as_relative_form(self):
        for host in ('example.org.', 'sub.example.org.', 'b\u00fccher.example.'):
            with self.subTest(host=host):
                self.assertEqual(tls_server_name(host), host[:-1])

    def test_unqualified_dns_names_and_ip_literals_are_unchanged(self):
        for host in ('example.org', 'localhost', '127.0.0.1', '::1', 'fe80::1%eth0'):
            with self.subTest(host=host):
                self.assertEqual(tls_server_name(host), host)


if __name__ == '__main__':
    unittest.main()
