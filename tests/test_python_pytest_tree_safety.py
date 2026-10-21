"""Regression tests for symlink-safe, bounded pytest command discovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import _pytest_suites_are_safe, python_test_command


class PytestTreeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tests = self.root / 'tests'
        self.tests.mkdir()
        (self.tests / 'test_safe.py').touch()

    def discover(self):
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
            return python_test_command(self.root)

    def make_link(self, source, target, *, directory=False):
        try:
            source.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')

    def test_regular_nested_nonpackage_is_safe(self):
        nested = self.tests / 'functional'
        nested.mkdir()
        (nested / 'test_nested.py').touch()
        self.assertTrue(_pytest_suites_are_safe(self.root))
        self.assertEqual(self.discover()['argv'][1:3], ['-m', 'pytest'])

    def test_nested_linked_test_module_is_rejected(self):
        nested = self.tests / 'functional'
        nested.mkdir()
        outside = self.root / 'outside.py'
        outside.touch()
        self.make_link(nested / 'test_external.py', outside)
        self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_nested_linked_directory_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.make_link(self.tests / 'linked', outside, directory=True)
        self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_linked_conftest_is_rejected(self):
        outside = self.root / 'outside.py'
        outside.touch()
        self.make_link(self.tests / 'conftest.py', outside)
        self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_singular_test_directory_checks_descendants(self):
        self.tests.rename(self.root / 'test')
        nested = self.root / 'test' / 'nested'
        nested.mkdir()
        outside = self.root / 'outside.py'
        outside.touch()
        self.make_link(nested / 'test_external.py', outside)
        self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_entry_cap_is_enforced(self):
        with patch('devpilot.python_tests._MAX_TEST_DISCOVERY_ENTRIES', 1):
            (self.tests / 'test_more.py').touch()
            self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_os_error_fails_closed(self):
        with patch('pathlib.Path.iterdir', side_effect=PermissionError('private location')):
            self.assertFalse(_pytest_suites_are_safe(self.root))

    def test_nested_link_must_not_select_pytest(self):
        nested = self.tests / 'fixtures'
        nested.mkdir()
        outside = self.root / 'external.py'
        outside.touch()
        self.make_link(nested / 'test_external.py', outside)
        command = self.discover()
        self.assertIsNone(command)

    def test_other_conventional_suite_must_not_select_pytest(self):
        other = self.root / 'test'
        other.mkdir()
        outside = self.root / 'external.py'
        outside.touch()
        self.make_link(other / 'test_external.py', outside)
        command = self.discover()
        self.assertIsNone(command)

    def test_root_level_pytest_cannot_bypass_unsafe_suite(self):
        (self.tests / 'test_safe.py').unlink()
        nested = self.tests / 'nested'
        nested.mkdir()
        outside = self.root / 'external.py'
        outside.touch()
        self.make_link(nested / 'test_external.py', outside)
        (self.root / 'example_test.py').touch()
        self.assertIsNone(self.discover())

    def test_unittest_behavior_remains_unchanged(self):
        nested = self.tests / 'fixtures'
        nested.mkdir()
        outside = self.root / 'outside.py'
        outside.touch()
        self.make_link(nested / 'test_external.py', outside)
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
            command = python_test_command(self.root)
        self.assertEqual(command['argv'][-2:], ['-s', 'tests'])


if __name__ == '__main__':
    unittest.main()
