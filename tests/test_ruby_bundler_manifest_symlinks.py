"""Linked Bundler manifests cannot establish a trustworthy Ruby test plan."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RubyBundlerManifestSymlinkTests(unittest.TestCase):
    def test_only_linked_gemfile_does_not_enable_rspec(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as external:
            root = Path(project)
            (root / 'spec').mkdir()
            (root / 'spec' / 'example_spec.rb').write_text('')
            target = Path(external) / 'Gemfile'
            target.write_text('')
            try:
                (root / 'Gemfile').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_only_linked_gems_rb_does_not_enable_minitest(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as external:
            root = Path(project)
            (root / 'test').mkdir()
            (root / 'test' / 'test_helper.rb').write_text('')
            (root / 'test' / 'sample_test.rb').write_text('')
            target = Path(external) / 'gems.rb'
            target.write_text('')
            try:
                (root / 'gems.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'gems.rb'}))

    def test_linked_default_manifest_blocks_regular_alternative(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as external:
            root = Path(project)
            (root / 'spec').mkdir()
            (root / 'spec' / 'example_spec.rb').write_text('')
            target = Path(external) / 'Gemfile'
            target.write_text('')
            (root / 'gems.rb').write_text('')
            try:
                (root / 'Gemfile').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'Gemfile', 'gems.rb'}))


if __name__ == '__main__':
    unittest.main()
