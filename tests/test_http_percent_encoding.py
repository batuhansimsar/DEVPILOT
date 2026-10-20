"""Regression tests for invalid percent escapes in HTTP probe targets."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class PercentEscapeNormalizationTests(unittest.TestCase):
    def test_stray_percent_is_encoded_without_mangling_valid_escapes(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/health%?q=100%&escaped=%2F&broken=%zz')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url,
                         'https://example.org/health%25?q=100%25&escaped=%2F&broken=%25zz')
        self.assertEqual(result['url'], 'https://example.org/health%25')
        self.assertNotIn('100%', str(result))
        self.assertTrue(result['healthy'])

    def test_trailing_percent_in_path_and_query_is_encoded(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 200
            result = http_check('http://example.org/ready%?value=%')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://example.org/ready%25?value=%25')
        self.assertEqual(result['url'], 'http://example.org/ready%25')

    def test_utf8_and_valid_percent_escapes_preserved(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/café%2F?q=λ%20x')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://example.org/caf%C3%A9%2F?q=%CE%BB%20x')
        self.assertEqual(result['url'], 'https://example.org/caf%C3%A9%2F')


if __name__ == '__main__':
    unittest.main()
