"""Regression tests for HTTP probe URL size limits."""

import unittest
from unittest.mock import patch

from devpilot.http_url_validation import MAX_HTTP_URL_LENGTH, validate_http_url_length


class HTTPURLLengthTests(unittest.TestCase):
    def test_exact_limit_is_allowed(self):
        validate_http_url_length('x' * MAX_HTTP_URL_LENGTH)

    def test_oversized_url_rejected_without_echoing_content(self):
        secret = 'private_query_token'
        with self.assertRaises(ValueError) as caught:
            validate_http_url_length('x' * MAX_HTTP_URL_LENGTH + secret)
        self.assertIn('8192-character limit', str(caught.exception))
        self.assertNotIn(secret, str(caught.exception))

    def test_non_string_input_rejected(self):
        for value in (None, 123, b'https://example.org/'):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'URL must be a string'):
                validate_http_url_length(value)


class HTTPURLIntegrationTests(unittest.TestCase):
    def test_http_probe_rejects_oversized_url_without_network_setup(self):
        from devpilot.httpcheck import http_check

        oversized = 'https://example.org/' + 'a' * MAX_HTTP_URL_LENGTH
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, '8192-character limit'):
                http_check(oversized)
        opener.assert_not_called()

    def test_http_probe_allows_url_at_limit(self):
        from devpilot.httpcheck import http_check

        prefix = 'https://example.org/'
        url = prefix + 'a' * (MAX_HTTP_URL_LENGTH - len(prefix))
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check(url)
        self.assertTrue(result['healthy'])
        opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
