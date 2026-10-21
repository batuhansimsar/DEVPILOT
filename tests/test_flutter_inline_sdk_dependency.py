"""Regression tests for inline Flutter SDK dependencies and false positives."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import _has_flutter_sdk_dependency, dart_test_command


class FlutterInlineSDKTests(unittest.TestCase):
    def test_inline_flutter_sdk_in_supported_sections(self):
        fixtures = (
            b'dependencies:\n  flutter: {sdk: flutter}\n',
            b'dev_dependencies:\n  "flutter_test": {"sdk": "flutter"} # comment\n',
            b"dependency_overrides:\n  'local_plugin': {'sdk': 'flutter'}\n",
        )
        for contents in fixtures:
            with self.subTest(contents=contents):
                self.assertTrue(_has_flutter_sdk_dependency(contents))
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / 'pubspec.yaml').write_bytes(contents)
                    (root / 'test').mkdir()
                    command = dart_test_command(root, {'pubspec.yaml'})
                    self.assertEqual(command['argv'], ['flutter', 'test'])

    def test_rejects_unrelated_or_malformed_inline_lookalikes(self):
        fixtures = (
            b'name: example\nmetadata:\n  flutter_test: {sdk: flutter}\n',
            b'dependencies:\n  flutter: "{sdk: flutter}"\n',
            b'dependencies:\n  flutter_test: {sdk: dart}\n',
            b'dependencies:\n  flutter_test: {sdk: flutter, path: local}\n',
            b'dependencies:\n  outer:\n    flutter_test: {sdk: flutter}\n',
        )
        for contents in fixtures:
            with self.subTest(contents=contents):
                self.assertFalse(_has_flutter_sdk_dependency(contents))

    def test_regular_multiline_dependency_still_supported(self):
        self.assertTrue(_has_flutter_sdk_dependency(
            b'dev_dependencies:\n  flutter_test:\n    sdk: flutter\n'))


if __name__ == '__main__':
    unittest.main()
