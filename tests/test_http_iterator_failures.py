"""Regression tests for status iterables that fail during validation."""

import unittest

from devpilot.httpcheck import http_check


class BrokenIterable:
    def __iter__(self):
        raise RuntimeError("sensitive iterator implementation detail")


class BrokenIterator:
    def __iter__(self):
        return self

    def __next__(self):
        raise RuntimeError("sensitive iterator implementation detail")


def broken_generator():
    yield 200
    raise RuntimeError("sensitive iterator implementation detail")


class HTTPStatusIteratorTests(unittest.TestCase):
    def test_iterable_creation_failure_is_invalid_input(self):
        with self.assertRaisesRegex(ValueError, r"^expected HTTP status codes"):
            http_check("http://127.0.0.1:1", expected_statuses=BrokenIterable())

    def test_iteration_failure_is_invalid_input(self):
        for iterable in (BrokenIterator(), broken_generator()):
            with self.subTest(iterable=type(iterable).__name__):
                with self.assertRaisesRegex(ValueError, r"^expected HTTP status codes"):
                    http_check("http://127.0.0.1:1", expected_statuses=iterable)


if __name__ == "__main__":
    unittest.main()
