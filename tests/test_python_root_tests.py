"""Root-level Python test discovery must match runner globs and avoid symlinks."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class RootPythonTestDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def discover(self, has_pytest):
        with patch('devpilot.python_tests.PathFinder.find_spec',
                   return_value=object() if has_pytest else None):
            return python_test_command(self.root)

    def test_root_pytest_module(self):
        (self.root / 'test_feature.py').write_text('def test_works(): pass\n')
        self.assertEqual(self.discover(True), {
            'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
            'reason': 'root-level pytest test files',
        })

    def test_root_unittest_module_without_pytest(self):
        (self.root / 'test_feature.py').write_text('import unittest\n')
        self.assertEqual(self.discover(False), {
            'ecosystem': 'Python',
            'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', '.'],
            'reason': 'root-level unittest test files',
        })

    def test_suffix_pytest_file_requires_pytest(self):
        (self.root / 'feature_test.py').touch()
        self.assertEqual(self.discover(True)['argv'], [sys.executable, '-m', 'pytest'])
        self.assertIsNone(self.discover(False))

    def test_root_nontest_module_does_not_trigger(self):
        (self.root / 'feature.py').touch()
        with patch('devpilot.python_tests.PathFinder.find_spec') as find_spec:
            self.assertIsNone(python_test_command(self.root))
        find_spec.assert_not_called()

    def test_root_symlinked_test_file_does_not_trigger(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'test_hidden.py'
            target.touch()
            try:
                (self.root / 'test_hidden.py').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.discover(True))

    def test_symlinked_directory_blocks_root_pytest(self):
        (self.root / 'test_feature.py').touch()
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / 'tests').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.discover(True))

    def test_existing_suite_preferred_over_root_files(self):
        (self.root / 'test_root.py').touch()
        tests = self.root / 'tests'
        tests.mkdir()
        (tests / 'test_nested.py').touch()
        self.assertEqual(self.discover(False)['argv'][-1], 'tests')
        self.assertEqual(self.discover(True)['reason'], 'tests directory (pytest importable)')

    def test_empty_test_directory_falls_back_to_root_unittest(self):
        (self.root / 'tests').mkdir()
        (self.root / 'test_root.py').touch()
        self.assertEqual(self.discover(False)['argv'][-1], '.')

    def test_unittest_command_runs_root_level_test(self):
        (self.root / 'test_actual.py').write_text(
            'import unittest\nclass RootTest(unittest.TestCase):\n'
            '    def test_example(self): self.assertEqual(2 + 2, 4)\n',
            encoding='utf-8',
        )
        command = self.discover(False)
        completed = subprocess.run(
            command['argv'], cwd=self.root, capture_output=True, text=True, timeout=10,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('Ran 1 test', completed.stderr)

    def test_root_symlink_blocks_otherwise_valid_module(self):
        (self.root / 'test_valid.py').touch()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'test_external.py'
            target.touch()
            try:
                (self.root / 'test_external.py').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.discover(True))
            self.assertIsNone(self.discover(False))

    def test_nested_symlink_in_conventional_suite_blocks_pytest(self):
        suite = self.root / 'tests'
        suite.mkdir()
        (suite / 'test_valid.py').touch()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'test_external.py'
            target.touch()
            try:
                (suite / 'test_external.py').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.discover(True))

    def test_root_invalid_unittest_name_not_discovered(self):
        (self.root / 'test-invalid.py').touch()
        self.assertIsNone(self.discover(False))

    def test_root_listing_limit_fails_closed(self):
        for index in range(4096):
            (self.root / f'f{index:04d}').touch()
        (self.root / 'test_feature.py').touch()
        self.assertIsNone(self.discover(True))


if __name__ == '__main__':
    unittest.main()
