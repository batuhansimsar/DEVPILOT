"""Long or UTF-8 expanded HTTP URLs must be rejected before network access."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import MAX_HTTP_URL_LENGTH, http_check


class HTTPURLLengthTests(unittest.TestCase):
    def test_rejects_oversized_raw_url_without_exposing_query(self):
        url = 'https://example.org/ready?token=private-' + 'x' * MAX_HTTP_URL_LENGTH
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'URL exceeds 8192-character limit') as caught:
                http_check(url)
            opener.assert_not_called()
        self.assertNotIn('private-', str(caught.exception))

    def test_rejects_unicode_url_that_expands_past_limit(self):
        # Three-byte Unicode codepoints expand to nine ASCII bytes each.
        url = 'https://example.org/' + '€' * 1000
        self.assertLess(len(url), MAX_HTTP_URL_LENGTH)
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'Encoded URL exceeds 8192-character limit'):
                http_check(url)
            opener.assert_not_called()

    def test_accepts_url_exactly_at_encoded_length_limit(self):
        prefix = 'https://example.org/'
        url = prefix + 'x' * (MAX_HTTP_URL_LENGTH - len(prefix))
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check(url)
            self.assertTrue(result['healthy'])
            self.assertEqual(opener.return_value.open.call_args.args[0].full_url, url)

    def test_normal_utf8_url_still_encodes_and_does_not_expose_query(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/café?token=private')
            self.assertTrue(result['healthy'])
            self.assertEqual(result['url'], 'https://example.org/caf%C3%A9')
            self.assertNotIn('private', str(result))


if __name__ == '__main__':
    unittest.main()
