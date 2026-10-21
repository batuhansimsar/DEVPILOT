"""Regression coverage for pytest-only modules in a singular test/ suite."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class SingularPytestDiscoveryTests(unittest.TestCase):
    def test_pytest_only_suffix_in_singular_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            (suite / 'example_test.py').write_text('def test_example(): assert True\n')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                command = python_test_command(root)
            self.assertEqual(command, {
                'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'pytest', 'test'],
                'reason': 'test directory (pytest importable)',
            })

    def test_pytest_only_suffix_does_not_select_empty_unittest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            (suite / 'example_test.py').write_text('def test_example(): assert True\n')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))

    def test_singular_unittest_fallback_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            (suite / 'test_example.py').write_text('import unittest\n')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command['argv'],
                             [sys.executable, '-m', 'unittest', 'discover', '-s', 'test'])

    def test_symlink_in_singular_pytest_suite_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            target = Path(outside) / 'example_test.py'
            target.write_text('def test_external(): assert False\n')
            try:
                (suite / 'example_test.py').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))


if __name__ == '__main__':
    unittest.main()
