"""Malformed HTTP responses should produce safe, structured probe failures."""

import unittest
from http.client import BadStatusLine, HTTPException, LineTooLong
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPMalformedResponseTests(unittest.TestCase):
    def test_malformed_responses_return_unreachable_without_leaking_details(self):
        for failure in (
            BadStatusLine('HTTP/0.0 malformed-secret'),
            LineTooLong('a-secret-status-line'),
            HTTPException('internal-secret'),
        ):
            with self.subTest(failure=type(failure).__name__):
                with patch('devpilot.httpcheck.build_opener') as opener:
                    opener.return_value.open.side_effect = failure
                    result = http_check('http://example.org/health?token=query-secret')
                self.assertEqual(result['url'], 'http://example.org/health')
                self.assertEqual(result['method'], 'HEAD')
                self.assertIs(result['reachable'], False)
                self.assertIs(result['healthy'], False)
                self.assertIsNone(result['status'])
                self.assertEqual(result['error'], type(failure).__name__)
                self.assertGreaterEqual(result['latency_ms'], 0)
                self.assertNotIn('secret', str(result))


if __name__ == '__main__':
    unittest.main()
