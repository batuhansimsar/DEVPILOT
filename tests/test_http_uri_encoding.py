"""Regression coverage for RFC 3986 punctuation in HTTP request targets."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPRequestTargetEncodingTests(unittest.TestCase):
    def test_braces_are_percent_encoded_in_path_and_query(self):
        with patch('devpilot.httpcheck.build_opener') as mocked_opener:
            mocked_opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('http://example.com/health{check}?tag={ready}&slash=%2F')
        self.assertTrue(result['healthy'])
        request = mocked_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url,
                         'http://example.com/health%7Bcheck%7D?tag=%7Bready%7D&slash=%2F')
        self.assertEqual(request.get_method(), 'HEAD')
        self.assertNotIn('tag=', result['url'])

    def test_valid_subdelimiters_are_not_changed(self):
        with patch('devpilot.httpcheck.build_opener') as mocked_opener:
            mocked_opener.return_value.open.return_value.__enter__.return_value.status = 204
            http_check("http://example.com/a!$&'()*+,;=:@b?x=$&'()*+,;=:@/z")
        request = mocked_opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url,
                         "http://example.com/a!$&'()*+,;=:@b?x=$&'()*+,;=:@/z")


if __name__ == '__main__':
    unittest.main()
