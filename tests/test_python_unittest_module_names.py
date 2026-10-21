"""Regression: invalid Python test filenames must not select unittest."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class UnittestModuleNameTests(unittest.TestCase):
    def test_invalid_module_names_do_not_trigger_unittest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test-invalid.py').write_text('')
            (tests / 'test spaces.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))

    def test_valid_module_after_invalid_names_still_selects_unittest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test-invalid.py').write_text('')
            (tests / 'test_valid.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command['argv'],
                             [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'])

    def test_invalid_plural_tests_fall_back_to_valid_singular_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test-invalid.py').write_text('')
            (root / 'test').mkdir()
            (root / 'test' / 'test_valid.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command['argv'][-1], 'test')

    def test_invalid_singular_suite_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'test-bad.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))


if __name__ == '__main__':
    unittest.main()
