"""A valid RSpec marker must not mask unsafe nested spec entries."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RSpecSuiteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.spec = self.root / 'spec'
        self.spec.mkdir()
        (self.root / 'Gemfile').touch()
        (self.spec / 'spec_helper.rb').touch()

    def test_regular_helper_without_spec_files_is_supported(self):
        self.assertEqual(ruby_test_command(self.root, {'Gemfile'})['argv'],
                         ['bundle', 'exec', 'rspec'])

    def test_linked_spec_file_rejected_even_with_helper(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'foreign_spec.rb'
            target.touch()
            try:
                (self.spec / 'foreign_spec.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_linked_nested_directory_rejected_even_with_helper(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.spec / 'nested').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_linked_file_rejected_when_regular_spec_found_first(self):
        (self.spec / 'a_spec.rb').touch()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'foreign_spec.rb'
            target.touch()
            try:
                (self.spec / 'z_spec.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_nested_regular_spec_is_supported_without_helper(self):
        (self.spec / 'spec_helper.rb').unlink()
        nested = self.spec / 'nested'
        nested.mkdir()
        (nested / 'calculator_spec.rb').touch()
        self.assertEqual(ruby_test_command(self.root, {'Gemfile'})['argv'],
                         ['bundle', 'exec', 'rspec'])

    def test_marker_cannot_hide_unreadable_tree_or_overlarge_tree(self):
        from unittest.mock import patch
        (self.spec / 'a_spec.rb').touch()
        extras = [self.spec / f'item-{i}' for i in range(4096)]
        with patch.object(Path, 'iterdir', return_value=iter([*extras, self.spec / 'a_spec.rb'])):
            self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))


if __name__ == '__main__':
    unittest.main()
