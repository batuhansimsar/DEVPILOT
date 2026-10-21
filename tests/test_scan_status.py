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

    def test_missing_or_malformed_problems_fail_closed(self):
        # An absent or false-y diagnostic field must not be treated as a
        # successful scan: the scanner's contract always returns a list.
        for problems in (None, False, 0, '', (), {}):
            with self.subTest(problems=problems):
                self.assertFalse(scan_succeeded({'truncated': False, 'problems': problems}))
        self.assertFalse(scan_succeeded({'truncated': False}))

    def test_unknown_diagnostics_do_not_invoke_boolean_hooks(self):
        class UntrustedDiagnostics:
            def __bool__(self):
                raise AssertionError('must not coerce malformed diagnostics')

        self.assertFalse(scan_succeeded({
            'truncated': False, 'problems': UntrustedDiagnostics(),
        }))


if __name__ == '__main__':
    unittest.main()
