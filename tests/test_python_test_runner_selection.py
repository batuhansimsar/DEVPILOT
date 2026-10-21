"""Python test discovery uses the chosen interpreter, not another venv's pytest."""

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
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                with patch('shutil.which', return_value='/other-venv/bin/pytest') as which:
                    command = python_test_command(root)
            self.assertEqual(command, {
                'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                'reason': 'tests directory',
            })
            which.assert_not_called()

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
