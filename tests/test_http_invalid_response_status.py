"""Malformed status metadata must not crash or leak information in HTTP health checks."""

import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from devpilot.httpcheck import http_check


class HTTPInvalidResponseStatusTests(unittest.TestCase):
    def test_invalid_status_is_safe_unreachable_result(self):
        for status in (None, True, False, 99, 600, '204-secret', 200.0, [], {}):
            with self.subTest(status=status), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = status
                result = http_check('https://example.org/health?secret=private')
            self.assertEqual(result['url'], 'https://example.org/health')
            self.assertFalse(result['reachable'])
            self.assertFalse(result['healthy'])
            self.assertIsNone(result['status'])
            self.assertEqual(result['error'], 'InvalidHTTPStatus')
            self.assertNotIn('secret', str(result))

    def test_valid_status_and_expected_custom_status(self):
        for status in (100, 204, 401, 599):
            with self.subTest(status=status), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = status
                result = http_check('https://example.org/health', expected_statuses={401})
            self.assertTrue(result['reachable'])
            self.assertEqual(result['status'], status)
            self.assertEqual(result['healthy'], status == 401)

    def test_invalid_http_error_status_is_safe(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.side_effect = HTTPError(
                'https://example.org/health?secret=private', 'bad-status', 'private', {}, None,
            )
            result = http_check('https://example.org/health?secret=private')
        self.assertFalse(result['reachable'])
        self.assertIsNone(result['status'])
        self.assertEqual(result['error'], 'InvalidHTTPStatus')
        self.assertNotIn('secret', str(result))


if __name__ == '__main__':
    unittest.main()
