"""Malformed internationalized HTTP URLs must not crash the CLI or start probes."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPUnicodeURLTests(unittest.TestCase):
    def test_raw_unicode_host_path_and_query_are_argument_errors(self):
        urls = (
            'http://exämple.org/ready',
            'http://example.org/café',
            'http://example.org/ready?query=λ',
        )
        with patch('devpilot.httpcheck.build_opener') as opener:
            for url in urls:
                with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'ASCII'):
                    http_check(url)
            opener.assert_not_called()

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
