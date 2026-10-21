"""Rails-only RSpec helper detection must be read-only and symlink safe."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class RubyRailsHelperDiscoveryTests(unittest.TestCase):
    def test_rails_helper_alone_enables_rspec_for_bundler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'rails_helper.rb').write_text('', encoding='utf-8')
            with patch('subprocess.run') as runner:
                command = ruby_test_command(root, {'Gemfile'})
                runner.assert_not_called()
            self.assertEqual(command['argv'], ['bundle', 'exec', 'rspec'])
            self.assertEqual(command['ecosystem'], 'Ruby')

    def test_rails_helper_does_not_enable_non_bundler_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'rails_helper.rb').write_text('', encoding='utf-8')
            self.assertIsNone(ruby_test_command(root, {'gems.locked'}))

    def test_linked_rails_helper_is_not_a_trusted_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            target = root / 'outside.rb'
            target.write_text('', encoding='utf-8')
            try:
                (root / 'spec' / 'rails_helper.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('file symlinks unsupported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_linked_spec_directory_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / 'external'
            outside.mkdir()
            (outside / 'rails_helper.rb').write_text('', encoding='utf-8')
            try:
                (root / 'spec').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unsupported')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))


if __name__ == '__main__':
    unittest.main()
