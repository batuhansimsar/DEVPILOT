"""Regression tests: bounded scans must not silently succeed when incomplete."""

import unittest

from devpilot.scan_status import scan_succeeded


class ScanStatusTests(unittest.TestCase):
    def test_complete_scan_without_problems_succeeds(self):
        self.assertTrue(scan_succeeded({'truncated': False, 'problems': []}))

    def test_truncated_scan_fails_even_without_problems(self):
        self.assertFalse(scan_succeeded({'truncated': True, 'problems': []}))

    def test_problems_fail_complete_scan(self):
        self.assertFalse(scan_succeeded({'truncated': False, 'problems': ['Permission denied']}))

    def test_missing_or_invalid_truncation_status_fails_closed(self):
        for report in ({'problems': []}, {'truncated': None, 'problems': []},
                       {'truncated': 'false', 'problems': []}):
            with self.subTest(report=report):
                self.assertFalse(scan_succeeded(report))

    def test_missing_problems_fails_closed(self):
        self.assertFalse(scan_succeeded({'truncated': False}))

    def test_malformed_falsey_problems_fails_closed(self):
        for problems in (None, False, 0, '', (), {}):
            with self.subTest(problems=problems):
                self.assertFalse(scan_succeeded({'truncated': False, 'problems': problems}))

    def test_malformed_nonempty_problems_fails_closed(self):
        for problems in ('warning', {'error': 'permission denied'}, True):
            with self.subTest(problems=problems):
                self.assertFalse(scan_succeeded({'truncated': False, 'problems': problems}))

    def test_non_mapping_report_fails_closed(self):
        for report in (None, [], False):
            with self.subTest(report=report):
                self.assertFalse(scan_succeeded(report))


if __name__ == '__main__':
    unittest.main()
