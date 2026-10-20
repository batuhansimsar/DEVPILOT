"""Raw Unicode paths and queries are encoded; Unicode hosts remain invalid."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPUnicodeURLTests(unittest.TestCase):
    def test_raw_unicode_host_is_argument_error(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'ASCII'):
                http_check('http://exämple.org/ready')
            opener.assert_not_called()

    def test_raw_unicode_path_and_query_are_percent_encoded(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            report = http_check('http://example.org/café?query=λ&already=%2F')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://example.org/caf%C3%A9?query=%CE%BB&already=%2F')
        self.assertEqual(report['url'], 'http://example.org/caf%C3%A9')
        self.assertTrue(report['healthy'])
        self.assertNotIn('query=', str(report))

    def test_reserved_braces_are_encoded_in_request_target(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            report = http_check('http://example.org/a{b}?item={value}')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://example.org/a%7Bb%7D?item=%7Bvalue%7D')
        self.assertEqual(report['url'], 'http://example.org/a%7Bb%7D')

    def test_encoded_unicode_path_is_accepted(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            report = http_check('http://example.org/caf%C3%A9?token=hidden')
        self.assertTrue(report['healthy'])
        self.assertEqual(report['status'], 204)
        self.assertNotIn('hidden', str(report))
        opener.assert_called_once()


if __name__ == '__main__':
    unittest.main()
