"""Refuse ambiguous percent-encoded HTTP authorities before networking."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPAuthorityEncodingTests(unittest.TestCase):
    def test_percent_encoded_hosts_rejected_before_network(self):
        for url in (
            'http://exa%6dple.org/ready',
            'https://example.org%2f.attacker.invalid/',
            'http://127.0.0.1%00.evil.invalid/',
            'http://[fe80::1%25eth0]/',
        ):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'percent escapes'):
                    http_check(url)
                opener.assert_not_called()

    def test_percent_encoded_path_and_query_still_work(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/%25ready?token=%20hidden')
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(result['url'], 'https://example.org/%25ready')
        self.assertEqual(request.full_url, 'https://example.org/%25ready?token=%20hidden')
        self.assertTrue(result['healthy'])


if __name__ == '__main__':
    unittest.main()
