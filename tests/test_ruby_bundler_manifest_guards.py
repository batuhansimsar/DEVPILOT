"""Regression tests for unsafe Bundler manifest path types."""

import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RubyBundlerManifestGuardTests(unittest.TestCase):
    def test_linked_alternative_is_not_hidden_by_regular_gemfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'example_spec.rb').write_text('')
            (root / 'Gemfile').write_text('')
            (root / 'target').write_text('')
            try:
                (root / 'gems.rb').symlink_to(root / 'target')
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(ruby_test_command(root, {'Gemfile', 'gems.rb'}))

    def test_directory_manifest_does_not_trigger_rspec(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'example_spec.rb').write_text('')
            (root / 'Gemfile').mkdir()
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_both_regular_manifests_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'spec').mkdir()
            (root / 'spec' / 'example_spec.rb').write_text('')
            (root / 'Gemfile').write_text('')
            (root / 'gems.rb').write_text('')
            self.assertEqual(
                ruby_test_command(root, {'Gemfile', 'gems.rb'})['argv'],
                ['bundle', 'exec', 'rspec'],
            )

    def test_gems_rb_minitest_still_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gems.rb').write_text('')
            (root / 'test').mkdir()
            (root / 'test' / 'test_helper.rb').write_text('')
            (root / 'test' / 'example_test.rb').write_text('')
            command = ruby_test_command(root, {'gems.rb'})
            self.assertEqual(command['argv'][:4], ['bundle', 'exec', 'ruby', '-Itest'])
