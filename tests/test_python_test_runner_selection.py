"""Python test discovery uses the chosen interpreter and avoids empty unittest runs."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PythonTestRunnerSelectionTests(unittest.TestCase):
    def test_pytest_module_selects_matching_interpreter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()) as spec:
                with patch('subprocess.Popen') as popen:
                    command = python_test_command(root)
            self.assertEqual(command, {
                'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': 'tests directory (pytest importable)',
            })
            spec.assert_called_once_with('pytest')
            popen.assert_not_called()

    def test_foreign_pytest_executable_is_not_sufficient(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_example.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                with patch('shutil.which', return_value='/other-venv/bin/pytest') as which:
                    command = python_test_command(root)
            self.assertEqual(command, {
                'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                'reason': 'tests directory',
            })
            which.assert_not_called()

    def test_empty_or_non_test_directory_is_not_discovered_without_pytest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'tests'
            tests.mkdir()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))
                (tests / 'helper.py').write_text('')
                self.assertIsNone(python_test_command(root))
                (tests / 'example_test.py').write_text('')
                self.assertIsNone(python_test_command(root))
                (tests / 'test_example.py').write_text('')
                self.assertIsNotNone(python_test_command(root))

    def test_only_nested_packages_are_discoverable_by_unittest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'tests' / 'sub'
            nested.mkdir(parents=True)
            (nested / 'test_case.py').write_text('')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))
                (nested / '__init__.py').write_text('')
                self.assertIsNotNone(python_test_command(root))

    def test_symlinked_test_files_are_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'tests').mkdir()
            target = Path(external) / 'test_external.py'
            target.write_text('')
            try:
                (root / 'tests' / 'test_external.py').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))

    def test_missing_tests_directory_not_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('devpilot.python_tests.PathFinder.find_spec') as spec:
                self.assertIsNone(python_test_command(root))
            spec.assert_not_called()

    def test_symlinked_tests_directory_not_discovered(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            try:
                (root / 'tests').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec') as spec:
                self.assertIsNone(python_test_command(root))
            spec.assert_not_called()


if __name__ == '__main__':
    unittest.main()
