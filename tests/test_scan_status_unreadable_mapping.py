"""Malformed third-party scan report mappings must fail closed."""

import unittest
from collections import UserDict

from devpilot.scan_status import scan_succeeded


class ScanStatusUnreadableMappingTests(unittest.TestCase):
    def test_mapping_get_errors_do_not_escape(self):
        for field in ('truncated', 'problems'):
            class UnreadableReport(dict):
                def get(self, key, default=None):
                    if key == field:
                        raise RuntimeError('sensitive input from report')
                    return super().get(key, default)

            with self.subTest(field=field):
                report = UnreadableReport(truncated=False, problems=[])
                self.assertIs(scan_succeeded(report), False)

    def test_standard_mapping_implementations_remain_supported(self):
        self.assertTrue(scan_succeeded(UserDict({'truncated': False, 'problems': []})))
        self.assertFalse(scan_succeeded(UserDict({'truncated': True, 'problems': []})))


if __name__ == '__main__':
    unittest.main()
