"""Discover standalone RSpec files without trusting linked or unrelated files."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RubySpecFilesDiscoveryTests(unittest.TestCase):
    def test_standalone_spec_file_detected_without_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'calculator_spec.rb').write_text('describe "calculator" do\nend\n', encoding='utf-8')
            result = ruby_test_command(root, {'Gemfile'})
            self.assertIsNotNone(result)
            self.assertEqual(result['argv'], ['bundle', 'exec', 'rspec'])

    def test_rspec_local_configuration_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / '.rspec-local').write_text('--format progress\n', encoding='utf-8')
            self.assertEqual(ruby_test_command(root, {'gems.rb'})['ecosystem'], 'Ruby')

    def test_unrelated_ruby_files_and_non_bundler_projects_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec'
            spec.mkdir()
            (spec / 'calculator.rb').write_text('', encoding='utf-8')
            (spec / 'calculator_spec.rb.bak').write_text('', encoding='utf-8')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
            (spec / 'calculator_spec.rb').write_text('', encoding='utf-8')
            self.assertIsNone(ruby_test_command(root, {'project.gemspec'}))

    def test_symlinked_spec_file_is_not_a_discovery_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec'
            spec.mkdir()
            target = root / 'elsewhere.rb'
            target.write_text('', encoding='utf-8')
            try:
                (spec / 'linked_spec.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_symlinked_rspec_local_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            target = root / 'elsewhere'
            target.write_text('', encoding='utf-8')
            try:
                (root / '.rspec-local').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))


if __name__ == '__main__':
    unittest.main()
