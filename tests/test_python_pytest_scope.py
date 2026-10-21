"""Pytest may only collect explicitly inspected conventional suite roots."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PytestScopeTests(unittest.TestCase):
    def test_explicitly_scopes_pytest_to_conventional_suites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_example.py').touch()
            (root / 'test').mkdir()
            (root / 'test_root.py').write_text('raise AssertionError("unexpected root collection")\n')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                command = python_test_command(root)
            self.assertEqual(command['argv'], [sys.executable, '-m', 'pytest', 'tests', 'test'])

    def test_single_pytest_suite_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_example.py').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                command = python_test_command(root)
            self.assertEqual(command['argv'], [sys.executable, '-m', 'pytest', 'tests'])

    def test_pytest_does_not_collect_unvalidated_root_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_example.py').touch()
            (root / 'tests' / 'test_safe.py').write_text('def test_pass():\n    assert True\n')
            (root / 'test_outside.py').write_text('def test_fail():\n    assert False\n')
            command = python_test_command(root)
            if command is None or command['argv'][2] != 'pytest':
                self.skipTest('pytest unavailable in selected interpreter')
            proc = subprocess.run(command['argv'], cwd=root, text=True, capture_output=True,
                                  timeout=30, check=False)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('1 passed', proc.stdout)


if __name__ == '__main__':
    unittest.main()
