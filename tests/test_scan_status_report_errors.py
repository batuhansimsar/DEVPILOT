"""Reported errors and unreadable fields must not appear as successful scans."""

import unittest
from collections import UserDict

from devpilot.scan_status import scan_succeeded


class ScanStatusReportErrorTests(unittest.TestCase):
    def test_explicit_error_always_fails_even_with_empty_problems(self):
        for error in ('read denied', '', False, 0, object()):
            with self.subTest(error_type=type(error).__name__):
                self.assertFalse(scan_succeeded({
                    'truncated': False, 'problems': [], 'error': error,
                }))

    def test_missing_or_null_error_preserves_successful_scans(self):
        for report in (
            {'truncated': False, 'problems': []},
            UserDict({'truncated': False, 'problems': [], 'error': None}),
        ):
            with self.subTest(type=type(report).__name__):
                self.assertTrue(scan_succeeded(report))

    def test_unreadable_error_field_fails_closed(self):
        class BrokenErrorReport(dict):
            def get(self, key, default=None):
                if key == 'error':
                    raise OSError('private filesystem path')
                return super().get(key, default)

        self.assertFalse(scan_succeeded(BrokenErrorReport(
            truncated=False, problems=[],
        ))


if __name__ == '__main__':
    unittest.main()
