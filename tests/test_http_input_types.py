"""Invalid HTTP probe arguments must fail clearly before any network activity."""

import math
import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPInputTypesTests(unittest.TestCase):
    def test_non_string_urls_rejected_before_building_opener(self):
        for url in (None, 123, b'http://example.com', ['http://example.com']):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'URL must be a string'):
                    http_check(url)
                opener.assert_not_called()

    def test_invalid_timeout_types_and_nonfinite_values_rejected(self):
        for timeout in (None, True, False, '2', object(), math.nan, math.inf, -math.inf, 0, 31):
            with self.subTest(timeout=timeout), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'timeout must be'):
                    http_check('http://example.com/', timeout)
                opener.assert_not_called()

    def test_valid_integer_and_float_timeouts(self):
        for timeout in (1, 0.5, 30.0):
            with self.subTest(timeout=timeout), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = 204
                result = http_check('http://example.com/ready', timeout)
                self.assertTrue(result['healthy'])
                self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], timeout)


if __name__ == '__main__':
    unittest.main()
