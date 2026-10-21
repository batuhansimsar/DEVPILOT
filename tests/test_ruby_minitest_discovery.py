"""Regression tests for safe Ruby test-unit/Minitest discovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class RubyMinitestDiscoveryTests(unittest.TestCase):
    def test_bundler_with_test_helper_discovers_test_loader(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'test_helper.rb').write_text('')
            command = ruby_test_command(root, {'Gemfile'})
            self.assertEqual(command['ecosystem'], 'Ruby')
            self.assertEqual(command['argv'][:5], ['bundle', 'exec', 'ruby', '-Itest', '-e'])
            self.assertIn('test/**/*_test.rb', command['argv'][5])
            self.assertIn('files.empty?', command['argv'][5])

    def test_rspec_wins_when_both_test_styles_are_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'spec_helper.rb').write_text('')
            (root / 'test').mkdir()
            (root / 'test' / 'test_helper.rb').write_text('')
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'], ['bundle', 'exec', 'rspec'])

    def test_unbundled_and_missing_helper_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
            (root / 'test' / 'test_helper.rb').write_text('')
            self.assertIsNone(ruby_test_command(root, {'gems.locked'}))

    def test_symlinked_helper_and_directory_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            outside = Path(elsewhere)
            (outside / 'test_helper.rb').write_text('')
            (root / 'test').mkdir()
            try:
                (root / 'test' / 'test_helper.rb').symlink_to(outside / 'test_helper.rb')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
            (root / 'test' / 'test_helper.rb').unlink()
            (root / 'test').rmdir()
            (root / 'test').symlink_to(outside, target_is_directory=True)
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_discovery_does_not_launch_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'test_helper.rb').write_text('')
            with patch('subprocess.run') as run, patch('subprocess.Popen') as popen:
                self.assertIsNotNone(ruby_test_command(root, {'Gemfile'}))
                run.assert_not_called()
                popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
