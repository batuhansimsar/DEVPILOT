"""Invalid URL ports must not leak their raw values in chained tracebacks."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPPortErrorPrivacyTests(unittest.TestCase):
    def test_invalid_port_error_does_not_chain_sensitive_text(self):
        urls = (
            'http://example.org:private-port-token/health?token=private-query-token',
            'https://example.org:65536/health?token=private-query-token',
        )
        for url in urls:
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, '^URL contains an invalid port$') as error:
                    http_check(url)
                self.assertIsNone(error.exception.__cause__)
                self.assertTrue(error.exception.__suppress_context__)
                opener.assert_not_called()

    def test_valid_explicit_port_preserves_request(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('http://example.org:8080/health?token=private-query-token')
        self.assertTrue(result['healthy'])
        self.assertEqual(result['url'], 'http://example.org:8080/health')


if __name__ == '__main__':
    unittest.main()
