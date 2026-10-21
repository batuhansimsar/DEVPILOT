"""Reject malformed DESCRIPTION contents before planning testthat package tests."""

import tempfile
import unittest
from pathlib import Path

from devpilot.r_tests import r_test_command


class RDescriptionManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'renv.lock').touch()
        suite = self.root / 'tests' / 'testthat'
        suite.mkdir(parents=True)
        (suite / 'test-valid.R').touch()
        (self.root / 'tests' / 'testthat.R').touch()
        self.description = self.root / 'DESCRIPTION'

    def command(self):
        return r_test_command(self.root, {'renv.lock', 'DESCRIPTION'})

    def test_valid_package_plan(self):
        self.description.write_text('Package: demo.package\nVersion: 1.0\n')
        self.assertEqual(self.command()['argv'], ['Rscript', '-e', 'testthat::test_local()'])

    def test_generic_or_invalid_package_name_rejected(self):
        for text in ('Project notes', 'Package: bad_name\n', 'Package: ../bad\n', 'Package: \n'):
            with self.subTest(text=text):
                self.description.write_text(text)
                self.assertIsNone(self.command())

    def test_oversized_manifest_rejected(self):
        self.description.write_bytes(b'Package: valid\n' + b'X' * 32769)
        self.assertIsNone(self.command())

    def test_linked_manifest_rejected(self):
        target = self.root / 'outside'
        target.write_text('Package: valid\n')
        try:
            self.description.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.command())


if __name__ == '__main__':
    unittest.main()
