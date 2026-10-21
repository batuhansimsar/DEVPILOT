"""Malformed scan results must fail closed instead of crashing callers."""

import unittest
from collections import UserDict

from devpilot.scan_status import scan_succeeded


class ScanStatusInputContractTests(unittest.TestCase):
    def test_non_mapping_results_fail_closed(self):
        for report in (None, False, 0, '', [], (), object()):
            with self.subTest(type=type(report).__name__):
                self.assertIs(scan_succeeded(report), False)

    def test_misleading_get_method_is_not_trusted(self):
        class PretendReport:
            def get(self, key, default=None):
                return False if key == 'truncated' else []

        self.assertIs(scan_succeeded(PretendReport()), False)

    def test_normal_mapping_implementations_continue_to_work(self):
        self.assertIs(scan_succeeded(UserDict({'truncated': False, 'problems': []})), True)
        self.assertIs(scan_succeeded(UserDict({'truncated': True, 'problems': []})), False)


if __name__ == '__main__':
    unittest.main()
