"""Missing HTTP response status must not crash health checks or dial real networks."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class _ResponseWithoutStatus:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class MissingHTTPStatusTests(unittest.TestCase):
    def test_missing_status_returns_invalid_response(self):
        with patch('devpilot.httpcheck.build_opener') as build:
            build.return_value.open.return_value = _ResponseWithoutStatus()
            result = http_check('https://example.org/health')
            build.return_value.open.assert_called_once()
        self.assertEqual(result['error'], 'InvalidHTTPStatus')
        self.assertIsNone(result['status'])
        self.assertFalse(result['reachable'])
        self.assertFalse(result['healthy'])
        self.assertEqual(result['url'], 'https://example.org/health')

    def test_valid_status_is_not_affected(self):
        with patch('devpilot.httpcheck.build_opener') as build:
            build.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/health')
        self.assertEqual(result['status'], 204)
        self.assertTrue(result['reachable'])
        self.assertTrue(result['healthy'])


if __name__ == '__main__':
    unittest.main()
