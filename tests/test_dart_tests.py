"""Regression tests for read-only Dart test-command discovery."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class DartTestDiscoveryTests(unittest.TestCase):
    def test_valid_dart_project_with_tests_is_discovered(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_text('name: example\n', encoding='utf-8')
            (root / 'test').mkdir()
            self.assertEqual(dart_test_command(root, {'pubspec.yaml'}), {
                'ecosystem': 'Dart', 'argv': ['dart', 'test'],
                'reason': 'pubspec.yaml with test directory',
            })

    def test_lockfile_only_and_missing_tests_are_not_testable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.lock').touch()
            self.assertIsNone(dart_test_command(root, {'pubspec.lock'}))
            (root / 'pubspec.yaml').touch()
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))
            (root / 'test').mkdir()
            self.assertIsNone(dart_test_command(root, set()))

    def test_symlinked_manifest_or_tests_are_not_used(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as external:
            root = Path(folder)
            outside = Path(external)
            (outside / 'pubspec.yaml').touch()
            (root / 'test').mkdir()
            try:
                (root / 'pubspec.yaml').symlink_to(outside / 'pubspec.yaml')
            except (OSError, NotImplementedError):
                self.skipTest('symlink unavailable')
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))
            (root / 'pubspec.yaml').unlink()
            (root / 'pubspec.yaml').touch()
            (root / 'test').rmdir()
            (outside / 'test').mkdir()
            (root / 'test').symlink_to(outside / 'test', target_is_directory=True)
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))


if __name__ == '__main__':
    unittest.main()
