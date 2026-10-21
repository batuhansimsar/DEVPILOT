"""A local RSpec marker must never hide a linked config/helper marker."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RSpecMixedMarkerLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'spec').mkdir()

    def link(self, marker: Path):
        outside = self.root / 'outside.rb'
        outside.touch()
        try:
            marker.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')

    def test_symlinked_global_rspec_config_rejected_despite_safe_helper(self):
        (self.root / 'spec' / 'spec_helper.rb').touch()
        self.link(self.root / '.rspec')
        self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_symlinked_local_config_rejected_despite_safe_global_config(self):
        (self.root / '.rspec').touch()
        self.link(self.root / '.rspec-local')
        self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_symlinked_helper_rejected_despite_safe_config(self):
        (self.root / '.rspec').touch()
        self.link(self.root / 'spec' / 'spec_helper.rb')
        self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_symlinked_rails_helper_rejected_despite_safe_config(self):
        (self.root / '.rspec').touch()
        self.link(self.root / 'spec' / 'rails_helper.rb')
        self.assertIsNone(ruby_test_command(self.root, {'Gemfile'}))

    def test_multiple_regular_markers_still_discover_rspec(self):
        (self.root / '.rspec').touch()
        (self.root / 'spec' / 'spec_helper.rb').touch()
        self.assertEqual(ruby_test_command(self.root, {'Gemfile'})['argv'], ['bundle', 'exec', 'rspec'])


if __name__ == '__main__':
    unittest.main()
