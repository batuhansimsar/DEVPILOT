"""Python projects may keep tests in a singular test/ directory."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class SingularPythonTestDirectoryTests(unittest.TestCase):
    def test_singular_directory_with_test_file_selects_pytest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test').mkdir()
            (root / 'test' / 'test_example.py').write_text('def test_ok(): pass\n', encoding='utf-8')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertEqual(python_test_command(root), {
                    'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest', 'test'],
                    'reason': 'test directory (pytest importable)',
                })

    def test_singular_directory_uses_unittest_without_pytest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test').mkdir()
            (root / 'test' / 'test_suite.py').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                self.assertEqual(python_test_command(root), {
                    'ecosystem': 'Python',
                    'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'test'],
                    'reason': 'test directory',
                })

    def test_unrelated_test_directory_does_not_trigger_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec') as spec:
                self.assertIsNone(python_test_command(root))
            spec.assert_not_called()

    def test_symlinked_test_entry_does_not_trigger_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test').mkdir()
            (root / 'outside.py').touch()
            try:
                (root / 'test' / 'test_external.py').symlink_to(root / 'outside.py')
            except (OSError, NotImplementedError):
                self.skipTest('file symlinks unavailable')
            self.assertIsNone(python_test_command(root))

    def test_symlinked_directory_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'real').mkdir()
            (root / 'real' / 'test_entry.py').touch()
            try:
                (root / 'test').symlink_to(root / 'real', target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unavailable')
            self.assertIsNone(python_test_command(root))

    def test_existing_plural_directory_remains_preferred(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_plural.py').touch()
            (root / 'test').mkdir()
            (root / 'test' / 'test_entry.py').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
                command = python_test_command(root)
            self.assertEqual(command['argv'][-2:], ['-s', 'tests'])
            self.assertEqual(command['reason'], 'tests directory')


if __name__ == '__main__':
    unittest.main()
