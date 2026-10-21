"""R testthat accepts both test- and test_ file prefixes."""

import tempfile
import unittest
from pathlib import Path

from devpilot.r_tests import r_test_command


class TestThatUnderscoreDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'project.Rproj').touch()
        (self.root / 'DESCRIPTION').write_text('Package: pkg\n', encoding='utf-8')
        self.suite = self.root / 'tests' / 'testthat'
        self.suite.mkdir(parents=True)
        (self.root / 'tests' / 'testthat.R').touch()

    def discover(self):
        return r_test_command(self.root, {'project.Rproj'})

    def test_underscore_test_with_uppercase_extension(self):
        (self.suite / 'test_feature.R').touch()
        self.assertIsNotNone(self.discover())

    def test_underscore_test_with_lowercase_extension(self):
        (self.suite / 'test_feature.r').touch()
        self.assertIsNotNone(self.discover())

    def test_underscore_lookalikes_do_not_count(self):
        (self.suite / 'test_feature.r.bak').touch()
        (self.suite / 'test_feature.txt').touch()
        (self.suite / 'helper_feature.r').touch()
        self.assertIsNone(self.discover())

    def test_linked_underscore_test_never_counts_as_safe(self):
        (self.suite / 'test-valid.R').touch()
        outside = self.root / 'outside.r'
        outside.touch()
        try:
            (self.suite / 'test_unsafe.r').symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
