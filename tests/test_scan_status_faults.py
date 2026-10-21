"""Bounded scan status must fail closed for broken mapping implementations."""

import unittest
from collections import UserDict
from collections.abc import Mapping

from devpilot.scan_status import scan_succeeded


class ScanStatusMappingFailuresTests(unittest.TestCase):
    def test_get_failure_is_not_a_success_or_an_exception(self):
        class BrokenGet(dict):
            def get(self, key, default=None):
                raise OSError('private scanner diagnostics')

        self.assertIs(scan_succeeded(BrokenGet(truncated=False, problems=[])), False)

    def test_mapping_get_failure_on_second_field_fails_closed(self):
        class PartiallyBrokenMapping(Mapping):
            def __iter__(self):
                return iter(('problems', 'truncated'))

            def __len__(self):
                return 2

            def __getitem__(self, key):
                if key == 'problems':
                    return []
                raise ValueError('private scanner diagnostics')

        self.assertIs(scan_succeeded(PartiallyBrokenMapping()), False)

    def test_valid_non_dict_mapping_still_succeeds(self):
        self.assertIs(scan_succeeded(UserDict(truncated=False, problems=[])), True)


if __name__ == '__main__':
    unittest.main()
