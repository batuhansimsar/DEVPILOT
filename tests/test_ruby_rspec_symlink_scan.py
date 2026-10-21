"""A regular RSpec helper/test must never hide a linked spec entry."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RSpecRecursiveSymlinkTests(unittest.TestCase):
    def test_linked_spec_file_is_rejected_despite_normal_spec(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            specs = root / 'spec'
            specs.mkdir()
            (specs / 'safe_spec.rb').touch()
            target = Path(elsewhere) / 'external_spec.rb'
            target.touch()
            try:
                (specs / 'external_spec.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_linked_nested_dir_is_rejected_when_helper_is_present(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            specs = root / 'spec'
            specs.mkdir()
            (specs / 'spec_helper.rb').touch()
            target = Path(elsewhere) / 'outside'
            target.mkdir()
            try:
                (specs / 'linked_specs').symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_real_spec_still_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = root / 'spec' / 'unit'
            specs.mkdir(parents=True)
            (specs / 'safe_spec.rb').touch()
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'], ['bundle', 'exec', 'rspec'])

    def test_marker_only_suite_still_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = root / 'spec'
            specs.mkdir()
            (specs / 'spec_helper.rb').touch()
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'], ['bundle', 'exec', 'rspec'])


if __name__ == '__main__':
    unittest.main()
