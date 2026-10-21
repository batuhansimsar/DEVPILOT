"""Do not recommend RSpec if another entry can escape its test tree."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import _MAX_DISCOVERY_ENTRIES, ruby_test_command


class RSpecTreeIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Gemfile').touch()
        self.spec = self.root / 'spec'
        self.spec.mkdir()

    def discover(self):
        return ruby_test_command(self.root, {'Gemfile'})

    def test_regular_marker_and_nested_spec_remain_detectable(self):
        (self.spec / 'spec_helper.rb').touch()
        nested = self.spec / 'models'
        nested.mkdir()
        (nested / 'user_spec.rb').touch()
        self.assertEqual(self.discover()['argv'], ['bundle', 'exec', 'rspec'])

    def test_marker_cannot_hide_linked_nested_directory(self):
        (self.spec / 'spec_helper.rb').touch()
        (self.spec / 'safe_spec.rb').touch()
        elsewhere = self.root / 'external'
        elsewhere.mkdir()
        try:
            (self.spec / 'linked').symlink_to(elsewhere, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_earlier_regular_spec_cannot_hide_dangling_link(self):
        (self.spec / 'first_spec.rb').touch()
        try:
            (self.spec / 'linked_spec.rb').symlink_to(self.root / 'missing.rb')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        # A sorted view is not guaranteed on real filesystems: exercise both
        # record orders, including when a safe spec is visited before a link.
        actual_iterdir = Path.iterdir
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                with patch.object(Path, 'iterdir', lambda p: iter(sorted(
                        actual_iterdir(p), key=lambda entry: entry.name,
                        reverse=reverse))):
                    self.assertIsNone(self.discover())

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFOs unavailable')
    def test_special_file_is_not_a_safe_rspec_suite_entry(self):
        (self.spec / 'spec_helper.rb').touch()
        try:
            os.mkfifo(self.spec / 'unexpected.pipe')
        except OSError:
            self.skipTest('FIFOs unavailable in this filesystem')
        self.assertIsNone(self.discover())

    def test_existing_marker_does_not_bypass_entry_limit(self):
        (self.spec / 'spec_helper.rb').touch()
        extras = [self.spec / f'noop-{i}' for i in range(_MAX_DISCOVERY_ENTRIES)]
        # A marker plus one additional item exceeds the fixed scan budget.
        with patch.object(Path, 'iterdir', return_value=iter([*extras, self.spec / 'late'])):
            self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
