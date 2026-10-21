"""An ordinary RSpec marker must not mask another linked RSpec config."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import ruby_test_command


class RSpecConfigSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'spec').mkdir()
        (self.root / 'spec' / 'spec_helper.rb').touch()
        (self.root / 'Gemfile').touch()

    def discover(self):
        return ruby_test_command(self.root, {'Gemfile'})

    def test_regular_helpers_still_select_rspec(self):
        self.assertEqual(self.discover()['argv'], ['bundle', 'exec', 'rspec'])

    def test_linked_rspec_config_is_rejected_despite_regular_spec_helper(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            target = Path(elsewhere) / 'settings'
            target.touch()
            for name in ('.rspec', '.rspec-local'):
                with self.subTest(name=name):
                    link = self.root / name
                    try:
                        link.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    with patch('subprocess.run') as run:
                        self.assertIsNone(self.discover())
                        run.assert_not_called()
                    link.unlink()

    def test_linked_alternative_helper_is_rejected(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            target = Path(elsewhere) / 'outside.rb'
            target.touch()
            link = self.root / 'spec' / 'rails_helper.rb'
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_dangling_config_link_is_rejected(self):
        link = self.root / '.rspec'
        try:
            link.symlink_to(self.root / 'missing')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
