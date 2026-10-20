"""Unexpected status-iterator exceptions should fail closed without network I/O."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class UnexpectedIteratorFailureTests(unittest.TestCase):
    def test_unexpected_iterator_errors_do_not_escape_or_start_network(self):
        class BrokenStatuses:
            def __iter__(self):
                yield 200
                raise OSError('private-token-must-never-appear')

        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, '^expected HTTP status codes') as raised:
                http_check('http://example.org/', expected_statuses=BrokenStatuses())
        opener.assert_not_called()
        self.assertNotIn('private-token', str(raised.exception))

    def test_unexpected_iterator_creation_errors_are_sanitized(self):
        class BrokenStatuses:
            def __iter__(self):
                raise KeyError('secret-filename')

        with patch('devpilot.httpcheck.build_opener') as opener:
            with self.assertRaisesRegex(ValueError, '^expected HTTP status codes') as raised:
                http_check('https://example.org/', expected_statuses=BrokenStatuses())
        opener.assert_not_called()
        self.assertNotIn('secret-filename', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
