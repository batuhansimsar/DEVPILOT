"""Ensure testthat discovery never approves linked suite entries."""

import tempfile
import unittest
from pathlib import Path

from devpilot.r_tests import r_test_command


class RTestSuiteSymlinkScopeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'renv.lock').touch()
        (self.root / 'DESCRIPTION').write_text('Package: demo\n', encoding='utf-8')
        self.suite = self.root / 'tests' / 'testthat'
        self.suite.mkdir(parents=True)
        (self.root / 'tests' / 'testthat.R').touch()
        (self.suite / 'test-local.R').touch()

    def test_regular_suite_with_auxiliary_file_is_accepted(self):
        (self.suite / 'helper-example.r').touch()
        self.assertIsNotNone(r_test_command(self.root, {'renv.lock'}))

    def test_lowercase_r_helper_symlink_is_rejected(self):
        target = self.root / 'external.r'
        target.touch()
        try:
            (self.suite / 'helper-external.r').symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(r_test_command(self.root, {'renv.lock'}))

    def test_linked_directory_is_rejected(self):
        (self.root / 'external-scripts').mkdir()
        try:
            (self.suite / 'helpers').symlink_to(self.root / 'external-scripts', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlinks unavailable')
        self.assertIsNone(r_test_command(self.root, {'renv.lock'}))

    def test_broken_non_r_symlink_is_rejected(self):
        try:
            (self.suite / 'payload.txt').symlink_to(self.root / 'does-not-exist')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(r_test_command(self.root, {'renv.lock'}))


if __name__ == '__main__':
    unittest.main()
