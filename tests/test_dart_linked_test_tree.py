"""Keep Dart/Flutter test discovery inside the selected repository root."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class LinkedTestTreeTests(unittest.TestCase):
    def test_nested_symlinked_test_file_is_not_scheduled(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text('name: app\n', encoding='utf-8')
            suite = root / 'test' / 'nested'
            suite.mkdir(parents=True)
            (suite / 'safe_test.dart').touch()
            self.assertIsNotNone(dart_test_command(root, {'pubspec.yaml'}))
            target = Path(outside) / 'outside_test.dart'
            target.touch()
            try:
                (suite / 'outside_test.dart').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))

    def test_nested_symlinked_directory_is_not_scheduled(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text('name: app\n', encoding='utf-8')
            suite = root / 'test' / 'nested'
            suite.mkdir(parents=True)
            try:
                (suite / 'external').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks unavailable')
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))

    def test_clean_flutter_suite_remains_discoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text(
                'name: app\ndependencies:\n  flutter:\n    sdk: flutter\n', encoding='utf-8')
            suite = root / 'test' / 'nested'
            suite.mkdir(parents=True)
            (suite / 'example_test.dart').touch()
            self.assertEqual(
                dart_test_command(root, {'pubspec.yaml'})['argv'], ['flutter', 'test'])


if __name__ == '__main__':
    unittest.main()
