"""Regression tests for strict HTTP DNS-label validation."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPDNSLabelValidationTests(unittest.TestCase):
    def test_invalid_dns_labels_fail_before_transport(self):
        for host in (
            'bad_name.example', '-leading.example', 'trailing-.example',
            'bad+name.example', 'bad!name.example', 'bad~name.example',
        ):
            with self.subTest(host=host), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'invalid DNS label') as caught:
                    http_check(f'https://{host}/ready?token=private-token')
                self.assertNotIn('private-token', str(caught.exception))
                opener.assert_not_called()

    def test_valid_hosts_still_work(self):
        for url in (
            'https://a-b.example/ready',
            'https://example.org./ready',
            'https://localhost/ready',
            'https://127.0.0.1/ready',
            'https://[::1]/ready',
        ):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = 204
                result = http_check(url)
                self.assertTrue(result['healthy'])
                opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
