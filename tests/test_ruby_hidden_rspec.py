"""RSpec discovery should agree with Ruby's dotfile-excluding glob behavior."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class HiddenRSpecTests(unittest.TestCase):
    def test_only_hidden_spec_paths_are_not_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec'
            (spec / '.private').mkdir(parents=True)
            (spec / '.private' / 'hidden_spec.rb').write_text('')
            (spec / '.hidden_spec.rb').write_text('')
            with patch('subprocess.run') as runner:
                self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
                runner.assert_not_called()

    def test_visible_nested_spec_still_discovered_alongside_hidden_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec'
            (spec / '.private').mkdir(parents=True)
            (spec / '.private' / 'hidden_spec.rb').write_text('')
            (spec / 'public').mkdir()
            (spec / 'public' / 'active_spec.rb').write_text('')
            self.assertEqual(ruby_test_command(root, {'Gemfile'})['argv'],
                             ['bundle', 'exec', 'rspec'])


if __name__ == '__main__':
    unittest.main()
