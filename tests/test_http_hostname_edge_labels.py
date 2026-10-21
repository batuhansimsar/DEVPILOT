"""Invalid HTTP DNS label edges are rejected before any network access."""

import unittest
from unittest.mock import patch

from devpilot.http_host_validation import validate_http_dns_labels
from devpilot.httpcheck import http_check


class HTTPDNSLabelTests(unittest.TestCase):
    def test_rejects_invalid_dns_label_boundaries_before_opening(self):
        for host in ('-api.example.org', 'api-.example.org',
                     'api.-edge.example.org', 'api.end-.org', 'api_name.example.org'):
            with self.subTest(host=host), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'invalid DNS label') as caught:
                    http_check(f'https://{host}/health?token=private-secret')
                opener.assert_not_called()
                self.assertNotIn('private-secret', str(caught.exception))

    def test_valid_hyphenated_idna_host_and_ipv6_still_work(self):
        for url in ('https://api-edge.example.org/health',
                    'https://xn--bcher-kva.example/health',
                    'https://example.org./health', 'http://[::1]:8080/health'):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = 204
                self.assertTrue(http_check(url)['healthy'])
                opener.assert_called_once()

    def test_direct_validator_rejects_oversize_label_and_empty_name(self):
        for host in (b'', b'.', b'a' * 64 + b'.example', b'a..b', b'a' * 254):
            with self.subTest(host=host), self.assertRaises(ValueError):
                validate_http_dns_labels(host)


if __name__ == '__main__':
    unittest.main()
