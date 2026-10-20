"""Reject ambiguous bracketed HTTP authorities without making a request."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPBracketedAuthorityTests(unittest.TestCase):
    def test_ipvfuture_authority_rejected_before_network(self):
        for url in (
            'https://[v1.example]/health',
            'http://[vF.alpha]:8080/ready',
        ):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'bracketed IPv6'):
                    http_check(url)
                opener.assert_not_called()

    def test_malformed_bracket_suffix_rejected_before_network(self):
        # urllib itself rejects this malformed authority, not the IPvFuture guard.
        for url in ('http://[::1]junk/ready', 'http://[::1]junk:8080/ready'):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaises(ValueError):
                    http_check(url)
                opener.assert_not_called()

    def test_valid_bracketed_ipv6_is_preserved_in_request_and_report(self):
        url = 'https://[2001:db8::1]:8443/ready?token=private'
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check(url)
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, url)
        self.assertEqual(result['url'], 'https://[2001:db8::1]:8443/ready')
        self.assertEqual(result['status'], 204)
        self.assertTrue(result['healthy'])
        self.assertNotIn('private', repr(result))


if __name__ == '__main__':
    unittest.main()
