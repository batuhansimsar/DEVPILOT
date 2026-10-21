"""Use Flutter's native test runner for Flutter packages, without executing code."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.dart_tests import dart_test_command


class FlutterTestCommandTests(unittest.TestCase):
    def test_flutter_sdk_uses_flutter_test(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_text(
                'name: app\ndependencies:\n  flutter:\n    sdk: flutter\n', encoding='utf-8')
            (root / 'test').mkdir()
            with patch('subprocess.run') as runner:
                result = dart_test_command(root, {'pubspec.yaml'})
                runner.assert_not_called()
            self.assertEqual(result['argv'], ['flutter', 'test'])
            self.assertEqual(result['ecosystem'], 'Dart')

    def test_plain_dart_uses_previous_command(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_text('name: package\n', encoding='utf-8')
            (root / 'test').mkdir()
            self.assertEqual(dart_test_command(root, {'pubspec.yaml'}), {
                'ecosystem': 'Dart', 'argv': ['dart', 'test'],
                'reason': 'pubspec.yaml with test directory',
            })

    def test_comments_do_not_trigger_flutter(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_text('# sdk: flutter\nname: package\n', encoding='utf-8')
            (root / 'test').mkdir()
            self.assertEqual(dart_test_command(root, {'pubspec.yaml'})['argv'], ['dart', 'test'])

    def test_oversized_manifest_has_no_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_bytes(b' ' * (128 * 1024 + 1))
            (root / 'test').mkdir()
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))

    def test_missing_or_symlinked_manifest_and_tests_have_no_plan(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as external:
            root = Path(folder)
            (root / 'test').mkdir()
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))
            target = Path(external) / 'pubspec.yaml'
            target.write_text('name: external\n', encoding='utf-8')
            try:
                (root / 'pubspec.yaml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))
            (root / 'pubspec.yaml').unlink()
            (root / 'pubspec.yaml').touch()
            (root / 'test').rmdir()
            (root / 'test').symlink_to(external, target_is_directory=True)
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))


if __name__ == '__main__':
    unittest.main()
