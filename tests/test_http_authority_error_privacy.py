"""Malformed HTTP URL authorities must not expose attacker-controlled text."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPAuthorityErrorPrivacyTests(unittest.TestCase):
    def test_parser_errors_do_not_echo_untrusted_authorities_or_issue_requests(self):
        urls = (
            'http://[private-host-token]/health?secret=private-query-token',
            'http://[private-host-token/health?secret=private-query-token',
            'http://[::invalid]/health?secret=private-query-token',
            'http://private-host\uff0ftoken/health?secret=private-query-token',
        )
        for url in urls:
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, '^URL contains an invalid authority$') as error:
                    http_check(url)
                self.assertEqual(str(error.exception), 'URL contains an invalid authority')
                self.assertIsNone(error.exception.__cause__)
                opener.assert_not_called()

    def test_valid_bracketed_ipv6_still_creates_request(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('http://[::1]:8080/health?token=private-query-token')
        self.assertEqual(result['url'], 'http://[::1]:8080/health')
        self.assertTrue(result['healthy'])
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, 'http://[::1]:8080/health?token=private-query-token')


if __name__ == '__main__':
    unittest.main()
