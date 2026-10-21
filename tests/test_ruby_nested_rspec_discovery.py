"""Nested Ruby RSpec suites must be discoverable without following links."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class NestedRSpecTests(unittest.TestCase):
    def test_nested_spec_without_helper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'spec' / 'models'
            nested.mkdir(parents=True)
            (nested / 'user_spec.rb').write_text('describe "user" do\nend\n')
            with patch('subprocess.run') as run:
                command = ruby_test_command(root, {'Gemfile'})
                run.assert_not_called()
            self.assertEqual(command['argv'], ['bundle', 'exec', 'rspec'])
            self.assertEqual(command['ecosystem'], 'Ruby')

    def test_linked_nested_directory_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            spec = root / 'spec'
            spec.mkdir()
            other = Path(outside) / 'models'
            other.mkdir()
            (other / 'outside_spec.rb').write_text('')
            try:
                (spec / 'models').symlink_to(other, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_linked_nested_file_and_backups_not_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'spec' / 'models'
            nested.mkdir(parents=True)
            (nested / 'user_spec.rb.bak').write_text('')
            target = root / 'outside.rb'
            target.write_text('')
            try:
                (nested / 'linked_spec.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_requires_bundler_manifest_even_with_nested_spec(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'spec' / 'requests'
            nested.mkdir(parents=True)
            (nested / 'api_spec.rb').write_text('')
            self.assertIsNone(ruby_test_command(root, {'project.gemspec'}))


if __name__ == '__main__':
    unittest.main()
