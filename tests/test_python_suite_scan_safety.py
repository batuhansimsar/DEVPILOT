"""Fail closed when Python test suites hide unsafe or oversized descendants."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PythonSuiteScanSafetyTests(unittest.TestCase):
    def test_linked_file_after_valid_test_blocks_both_runners(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_safe.py').touch()
            try:
                (tests / 'test_outside.py').symlink_to(Path(outside) / 'test_outside.py')
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            for pytest_available in (None, object()):
                with self.subTest(pytest=pytest_available is not None), patch(
                    'devpilot.python_tests.PathFinder.find_spec', return_value=pytest_available
                ):
                    self.assertIsNone(python_test_command(root))

    def test_linked_nested_directory_blocks_pytest(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_safe.py').touch()
            try:
                (tests / 'external').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))

    def test_oversized_suite_with_early_test_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_safe.py').touch()
            for number in range(4096):
                (tests / f'fixture_{number:04d}.txt').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))

    def test_importable_nested_unittest_suite_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pkg = root / 'tests' / 'nested'
            pkg.mkdir(parents=True)
            (pkg / '__init__.py').touch()
            (pkg / 'test_case.py').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                result = python_test_command(root)
            self.assertEqual(result['argv'][-3:], ['discover', '-s', 'tests'])

    def test_empty_suite_does_not_offer_an_empty_test_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))


if __name__ == '__main__':
    unittest.main()
