"""Regression coverage for DNS label validation before HTTP networking."""

import unittest

from devpilot.http_url_validation import validate_dns_hostname_labels


class DNSHostnameLabelTests(unittest.TestCase):
    def test_allows_maximum_size_label_and_terminal_root_dot(self):
        for hostname in (b'a' * 63 + b'.example', b'example.org.', b'127.0.0.1'):
            with self.subTest(hostname=hostname):
                validate_dns_hostname_labels(hostname)

    def test_rejects_empty_or_oversized_labels_without_echoing_input(self):
        for hostname in (b'', b'.example.org', b'example..org', b'example.org..',
                         b'a' * 64 + b'.org', b'.', b'-bad.example',
                         b'bad-.example', b'bad_name.example', b'bad!name.example'):
            with self.subTest(hostname=hostname), self.assertRaises(ValueError) as caught:
                validate_dns_hostname_labels(hostname)
            if hostname:
                self.assertNotIn(hostname.decode('ascii'), str(caught.exception))


class HTTPProbeDNSIntegrationTests(unittest.TestCase):
    def test_invalid_dns_labels_rejected_before_network_setup(self):
        from unittest.mock import patch
        from devpilot.httpcheck import http_check

        for hostname in ('-bad.example', 'bad-.example',
                         'bad_name.example', 'bad!name.example'):
            with self.subTest(hostname=hostname), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'DNS label'):
                    http_check(f'https://{hostname}/health')
                opener.assert_not_called()

    def test_legal_terminal_root_dot_still_reaches_transport(self):
        from unittest.mock import patch
        from devpilot.httpcheck import http_check

        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org./health')
        self.assertTrue(result['healthy'])
        opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
