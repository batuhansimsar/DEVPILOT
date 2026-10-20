"""Malformed Unicode URL input must be rejected before network I/O."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPUnpairedSurrogateTests(unittest.TestCase):
    def test_surrogates_are_rejected_without_network_access(self):
        urls = (
            'http://example.org/ready\ud800',
            'https://example.org/ready?token=\udfff',
            'http://example.org/#\ud800',
        )
        for url in urls:
            with self.subTest(url_type=url.split('://')[0]), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, '^URL must not contain unpaired Unicode surrogates$') as error:
                    http_check(url)
                self.assertNotIn('token=', str(error.exception))
                opener.assert_not_called()

    def test_valid_unicode_still_percent_encodes(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('http://example.org/caf\u00e9?term=\u03bb')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://example.org/caf%C3%A9?term=%CE%BB')
        self.assertEqual(result['url'], 'http://example.org/caf%C3%A9')
        self.assertTrue(result['healthy'])


if __name__ == '__main__':
    unittest.main()
