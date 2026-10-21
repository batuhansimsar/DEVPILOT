"""RSpec discovery requires a genuine Bundler project and local RSpec marker."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class RubyTestDiscoveryTests(unittest.TestCase):
    def test_gemfile_with_spec_helper_discovers_rspec(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'spec_helper.rb').write_text('', encoding='utf-8')
            command = ruby_test_command(root, {'Gemfile'})
        self.assertEqual(command, {
            'ecosystem': 'Ruby',
            'argv': ['bundle', 'exec', 'rspec'],
            'reason': 'Bundler manifest and RSpec configuration',
        })

    def test_alternative_bundler_manifest_and_dot_rspec(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / '.rspec').write_text('--format progress', encoding='utf-8')
            self.assertEqual(ruby_test_command(root, {'gems.rb'})['argv'], ['bundle', 'exec', 'rspec'])

    def test_ambiguous_or_non_bundler_projects_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'spec_helper.rb').write_text('', encoding='utf-8')
            for names in ({'gems.locked'}, {'sample.gemspec'}, set()):
                with self.subTest(names=names):
                    self.assertIsNone(ruby_test_command(root, names))
            (root / 'spec' / 'spec_helper.rb').unlink()
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_symlinked_spec_directory_does_not_trigger_discovery(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            outside = Path(elsewhere)
            (outside / 'spec_helper.rb').write_text('', encoding='utf-8')
            try:
                (root / 'spec').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks not supported')
            (root / '.rspec').write_text('', encoding='utf-8')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_symlinked_rspec_marker_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            (root / 'spec').mkdir()
            marker = Path(elsewhere) / 'settings'
            marker.write_text('', encoding='utf-8')
            try:
                (root / '.rspec').symlink_to(marker)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_discovery_never_executes_external_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / '.rspec').write_text('', encoding='utf-8')
            with patch('subprocess.run') as run:
                self.assertIsNotNone(ruby_test_command(root, {'Gemfile'}))
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
