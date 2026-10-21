"""Regression coverage for lower-case R testthat scripts and linked helpers."""

import tempfile
import unittest
from pathlib import Path

from devpilot.r_tests import r_test_command


class RScriptCaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'renv.lock').touch()
        (self.root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
        tests = self.root / 'tests'
        self.suite = tests / 'testthat'
        self.suite.mkdir(parents=True)
        (tests / 'testthat.R').touch()

    def discover(self):
        return r_test_command(self.root, {'renv.lock'})

    def test_lowercase_r_test_file_is_discoverable(self):
        (self.suite / 'test-example.r').touch()
        self.assertEqual(self.discover()['argv'],
                         ['Rscript', '-e', 'testthat::test_local()'])

    def test_lowercase_r_symlinked_test_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.r'
            target.touch()
            (self.suite / 'test-local.R').touch()
            try:
                (self.suite / 'test-outside.r').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_lowercase_r_symlinked_helper_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'helper.r'
            target.touch()
            (self.suite / 'test-local.R').touch()
            try:
                (self.suite / 'helper-env.r').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_lowercase_backup_does_not_count_as_test(self):
        (self.suite / 'test-local.r.bak').touch()
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
