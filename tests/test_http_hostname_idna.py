"""HTTP checks reject malformed DNS names before opening any sockets."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPHostnameIDNATests(unittest.TestCase):
    def test_invalid_dns_labels_rejected_before_request(self):
        for host in ('a' * 64 + '.example.org', 'api..example.org',
                     'a' * 64 + '.private.internal'):
            with self.subTest(host=host), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'invalid IDNA hostname') as error:
                    http_check(f'https://{host}/health?token=private-value')
                self.assertNotIn('private-value', str(error.exception))
                opener.assert_not_called()

    def test_valid_dns_name_and_ipv6_remain_supported(self):
        for url in ('https://example.org/health', 'http://[::1]:8080/health'):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = 204
                result = http_check(url)
                self.assertTrue(result['healthy'])
                opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
