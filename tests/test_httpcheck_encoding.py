"""Regression tests for safe HTTP health-check URL normalization."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPCheckEncodingTests(unittest.TestCase):
    def test_invalid_uri_characters_are_percent_encoded(self):
        with patch('devpilot.httpcheck.build_opener') as mocked:
            mocked.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.test/a{b}?item={value}&ok=yes')
            request = mocked.return_value.open.call_args.args[0]
        self.assertTrue(result['healthy'])
        self.assertEqual(
            request.full_url,
            'https://example.test/a%7Bb%7D?item=%7Bvalue%7D&ok=yes',
        )

    def test_preencoded_url_is_not_double_encoded(self):
        with patch('devpilot.httpcheck.build_opener') as mocked:
            mocked.return_value.open.return_value.__enter__.return_value.status = 204
            http_check('https://example.test/a%7Bb%7D?item=%7Bvalue%7D')
            request = mocked.return_value.open.call_args.args[0]
        self.assertEqual(
            request.full_url,
            'https://example.test/a%7Bb%7D?item=%7Bvalue%7D',
        )

    def test_legal_delimiters_are_preserved(self):
        with patch('devpilot.httpcheck.build_opener') as mocked:
            mocked.return_value.open.return_value.__enter__.return_value.status = 204
            http_check('https://example.test/a;b/c?key=x+y&other=z')
            request = mocked.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://example.test/a;b/c?key=x+y&other=z')


if __name__ == '__main__':
    unittest.main()
