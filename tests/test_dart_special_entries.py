"""Dart test discovery must reject filesystem nodes that are not regular files."""

import os
import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class DartSpecialEntryTests(unittest.TestCase):
    def test_fifo_in_test_directory_is_rejected(self):
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFOs are unavailable on this platform')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text('name: example\n', encoding='utf-8')
            suite = root / 'test' / 'nested'
            suite.mkdir(parents=True)
            (suite / 'example_test.dart').write_text('void main() {}\n', encoding='utf-8')
            self.assertEqual(dart_test_command(root, {'pubspec.yaml'})['argv'],
                             ['dart', 'test'])
            try:
                os.mkfifo(suite / 'untrusted.pipe')
            except OSError as exc:
                self.skipTest(f'FIFOs cannot be created: {exc.strerror}')
            self.assertIsNone(dart_test_command(root, {'pubspec.yaml'}))

    def test_flutter_regular_suite_is_still_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text(
                'name: app\ndependencies:\n  flutter:\n    sdk: flutter\n', encoding='utf-8')
            suite = root / 'test'
            suite.mkdir()
            (suite / 'widget_test.dart').touch()
            self.assertEqual(dart_test_command(root, {'pubspec.yaml'})['argv'],
                             ['flutter', 'test'])


if __name__ == '__main__':
    unittest.main()
