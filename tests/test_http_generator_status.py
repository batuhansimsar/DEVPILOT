"""Regression coverage for consumable expected-status iterators."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class ExpectedStatusesIteratorTests(unittest.TestCase):
    def test_generator_matching_code_is_healthy(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.invalid/health', expected_statuses=(code for code in [204, 401]))
        self.assertTrue(result['reachable'])
        self.assertTrue(result['healthy'])
        self.assertEqual(result['status'], 204)

    def test_empty_iterator_rejected_before_network(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'expected HTTP status codes'):
                http_check('https://example.invalid/health', expected_statuses=iter(()))
            opener.assert_not_called()

    def test_invalid_generator_rejected_before_network(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'expected HTTP status codes'):
                http_check('https://example.invalid/health', expected_statuses=(code for code in [204, True]))
            opener.assert_not_called()

    def test_unbounded_generator_is_rejected_promptly(self):
        def endless():
            while True:
                yield 204
        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, 'expected HTTP status codes'):
                http_check('https://example.invalid/health', expected_statuses=endless())
            opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
