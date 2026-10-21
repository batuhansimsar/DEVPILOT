"""Pytest must not collect linked root-level modules or configuration."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PytestRootSymlinkTests(unittest.TestCase):
    def _check_linked_root_module(self, linked_name, with_suite):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            if with_suite:
                (root / 'tests').mkdir()
                (root / 'tests' / 'test_safe.py').touch()
            else:
                (root / 'test_safe.py').touch()
            target = Path(outside) / linked_name
            target.touch()
            try:
                (root / linked_name).symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))

    def test_root_conftest_symlink_rejected_with_tests_directory(self):
        self._check_linked_root_module('conftest.py', with_suite=True)

    def test_root_test_symlink_rejected_with_tests_directory(self):
        self._check_linked_root_module('test_outside.py', with_suite=True)

    def test_root_test_symlink_rejected_without_tests_directory(self):
        self._check_linked_root_module('test_outside.py', with_suite=False)


if __name__ == '__main__':
    unittest.main()
