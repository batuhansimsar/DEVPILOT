"""Do not recommend unittest discovery that would import linked external modules."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import _has_unittest_tests, python_test_command


class LinkedUnittestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.tests = self.root / 'tests'
        self.tests.mkdir()
        (self.tests / 'test_safe.py').touch()

    def select_without_pytest(self):
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
            return python_test_command(self.root)

    def test_regular_suite_still_selects_unittest(self):
        self.assertEqual(self.select_without_pytest()['argv'][-2:], ['-s', 'tests'])

    def test_late_symlinked_test_module_rejects_entire_suite(self):
        target = self.root / 'external.py'
        target.touch()
        try:
            (self.tests / 'test_outside.py').symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertFalse(_has_unittest_tests(self.tests))
        self.assertIsNone(self.select_without_pytest())

    def test_symlinked_importable_nested_package_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / '__init__.py').touch()
        try:
            (self.tests / 'external_package').symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.select_without_pytest())

    def test_symlinked_nested_init_rejected(self):
        pkg = self.tests / 'pkg'
        pkg.mkdir()
        target = self.root / 'external.py'
        target.touch()
        try:
            (pkg / '__init__.py').symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.select_without_pytest())

    def test_nonimportable_nested_dir_does_not_trigger_rejection(self):
        nested = self.tests / 'unimportable'
        nested.mkdir()
        target = self.root / 'external.py'
        target.touch()
        try:
            (nested / 'test_outside.py').symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNotNone(self.select_without_pytest())


if __name__ == '__main__':
    unittest.main()
