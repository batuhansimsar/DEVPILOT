"""Prefer discoverable unittest suites when both Python test folders exist."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PythonTestFallbackTests(unittest.TestCase):
    def make_project(self, root):
        (root / 'tests').mkdir()
        (root / 'tests' / 'README.md').write_text('integration fixtures\n')
        (root / 'test').mkdir()
        (root / 'test' / 'test_example.py').write_text('import unittest\n')

    def test_falls_back_to_singular_suite_when_pytest_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command, {
                'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'test'],
                'reason': 'test directory',
            })

    def test_prefers_plural_suite_when_it_contains_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            (root / 'tests' / 'test_plural.py').write_text('import unittest\n')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command['argv'][-1], 'tests')

    def test_keeps_pytest_selection_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                command = python_test_command(root)
            self.assertEqual(command['argv'], [sys.executable, '-m', 'pytest'])
            self.assertIn('tests directory', command['reason'])

    def test_does_not_follow_linked_fallback(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            (root / 'tests').mkdir()
            (Path(elsewhere) / 'test_example.py').touch()
            try:
                (root / 'test').symlink_to(elsewhere, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertIsNone(python_test_command(root))


if __name__ == '__main__':
    unittest.main()
