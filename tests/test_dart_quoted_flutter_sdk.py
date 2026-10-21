"""Valid YAML SDK scalar quoting must not misselect Dart's test runner."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class QuotedFlutterSDKTests(unittest.TestCase):
    def test_quoted_and_unquoted_flutter_declarations_use_flutter_runner(self):
        for sdk in ('flutter', '"flutter"', "'flutter'"):
            with self.subTest(sdk=sdk), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'test').mkdir()
                (root / 'pubspec.yaml').write_text(
                    'name: sample\ndev_dependencies:\n'
                    f'  flutter_test:\n    sdk: {sdk} # Flutter SDK\n',
                    encoding='utf-8',
                )
                command = dart_test_command(root, {'pubspec.yaml'})
                self.assertEqual(command['argv'], ['flutter', 'test'])
                self.assertEqual(command['reason'], 'Flutter SDK dependency and test directory')

    def test_unrelated_or_malformed_flutter_strings_use_dart_runner(self):
        for sdk in ('flutterish', '"flutterish"', "'flutter", '"flutter"suffix'):
            with self.subTest(sdk=sdk), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'test').mkdir()
                (root / 'pubspec.yaml').write_text(
                    f'name: sample\ndependencies:\n  other:\n    sdk: {sdk}\n',
                    encoding='utf-8',
                )
                command = dart_test_command(root, {'pubspec.yaml'})
                self.assertEqual(command['argv'], ['dart', 'test'])


if __name__ == '__main__':
    unittest.main()
