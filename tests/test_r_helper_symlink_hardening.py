"""Testthat discovery must not approve linked helper/setup R scripts."""

import tempfile
import unittest
from pathlib import Path
from devpilot.r_tests import r_test_command


class RHelperSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'project'
        self.suite = self.root / 'tests' / 'testthat'
        self.suite.mkdir(parents=True)
        (self.root / 'project.Rproj').touch()
        (self.root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
        (self.root / 'tests' / 'testthat.R').touch()
        (self.suite / 'test-safe.R').touch()

    def discover(self):
        return r_test_command(self.root, {'project.Rproj'})

    def test_regular_helpers_do_not_block_discovery(self):
        (self.suite / 'helper-common.R').touch()
        (self.suite / 'setup-data.R').touch()
        self.assertIsNotNone(self.discover())

    def test_linked_helpers_and_setups_block_discovery(self):
        self.assertIsNotNone(self.discover())
        outside = self.root / 'outside.R'
        outside.touch()
        for name in ('helper-common.R', 'setup-data.R', 'helper.R'):
            with self.subTest(name=name):
                link = self.suite / name
                try:
                    link.symlink_to(outside)
                except (OSError, NotImplementedError):
                    self.skipTest('File symlinks unavailable')
                self.assertIsNone(self.discover())
                link.unlink()

    def test_symlinked_test_also_blocks_discovery_with_regular_test(self):
        target = self.root / 'outside.R'
        target.touch()
        link = self.suite / 'test-bad.R'
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('File symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_excessively_large_suite_does_not_trigger_discovery(self):
        for i in range(4096):
            (self.suite / f'fixture-{i}.txt').touch()
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
