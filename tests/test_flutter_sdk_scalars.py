"""Flutter test discovery accepts valid YAML scalars and line endings."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class FlutterSDKScalarTests(unittest.TestCase):
    def test_quoted_and_crlf_sdk_values(self):
        values = (
            b'flutter', b'"flutter"', b"'flutter'",
            b'flutter # SDK marker', b'"flutter" # SDK marker',
        )
        for value in values:
            for newline in (b'\n', b'\r\n'):
                with self.subTest(value=value, newline=newline):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        (root / 'test').mkdir()
                        (root / 'pubspec.yaml').write_bytes(
                            newline.join((b'name: example', b'dependencies:',
                                          b'  flutter:', b'    sdk: ' + value)) + newline
                        )
                        self.assertEqual(
                            dart_test_command(root, {'pubspec.yaml'})['argv'],
                            ['flutter', 'test'],
                        )

    def test_lookalikes_do_not_select_flutter(self):
        for value in (b'flutterish', b'"flutterish"', b"'flutter '" , b'flutter extra'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'test').mkdir()
                (root / 'pubspec.yaml').write_bytes(
                    b'name: example\ndependencies:\n  unrelated:\n    sdk: ' + value + b'\n'
                )
                self.assertEqual(
                    dart_test_command(root, {'pubspec.yaml'})['argv'],
                    ['dart', 'test'],
                )


if __name__ == '__main__':
    unittest.main()
