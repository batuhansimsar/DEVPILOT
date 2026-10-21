"""Prevent unbounded recursive scans during Ruby test discovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import _has_test_file, ruby_test_command


class RubyBoundedDiscoveryTests(unittest.TestCase):
    def test_deep_nested_rspec_and_minitest_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec' / 'models').mkdir(parents=True)
            (root / 'spec' / 'models' / 'user_spec.rb').touch()
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'], ['bundle', 'exec', 'rspec'])
            (root / 'spec' / 'models' / 'user_spec.rb').unlink()
            (root / 'test' / 'nested').mkdir(parents=True)
            (root / 'test' / 'test_helper.rb').touch()
            (root / 'test' / 'nested' / 'user_test.rb').touch()
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'][:3], ['bundle', 'exec', 'ruby'])

    def test_hidden_or_linked_minitest_files_do_not_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'test'
            (tests / '.hidden').mkdir(parents=True)
            (tests / 'test_helper.rb').touch()
            (tests / '.hidden' / 'secret_test.rb').touch()
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
            target = root / 'outside_test.rb'
            target.touch()
            try:
                (tests / 'linked_test.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlink not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_large_tree_stops_before_late_test_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'spec'
            tests.mkdir()
            late = tests / 'late_spec.rb'
            late.touch()
            noise = [tests / f'missing-{index}' for index in range(4096)]
            with patch.object(Path, 'iterdir', return_value=iter([*noise, late])):
                self.assertFalse(_has_test_file(tests, '_spec.rb'))


if __name__ == '__main__':
    unittest.main()
