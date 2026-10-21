"""Only known Flutter SDK packages should select the Flutter test runner."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class FlutterSDKPackageNameTests(unittest.TestCase):
    def select(self, manifest: bytes) -> list[str]:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test').mkdir()
            (root / 'pubspec.yaml').write_bytes(manifest)
            return dart_test_command(root, {'pubspec.yaml'})['argv']

    def test_known_sdk_packages_include_flutter_runner(self):
        for name in (b'flutter', b'flutter_test', b'flutter_localizations',
                     b'flutter_driver', b'flutter_web_plugins',
                     b'flutter_tools', b'flutter_gpu', b'integration_test'):
            for quote in (b'', b"'", b'"'):
                with self.subTest(name=name, quote=quote):
                    data = (b'dev_dependencies:\n  ' + quote + name + quote
                            + b':\n    sdk: flutter\n')
                    self.assertEqual(self.select(data), ['flutter', 'test'])

    def test_unknown_or_deceptively_similar_packages_do_not_select_flutter(self):
        for name in (b'other', b'flutterish', b'flutter_test_extra', b'integration_test2'):
            for quote in (b'', b"'", b'"'):
                with self.subTest(name=name, quote=quote):
                    data = (b'dependencies:\n  ' + quote + name + quote
                            + b':\n    sdk: flutter\n')
                    self.assertEqual(self.select(data), ['dart', 'test'])

    def test_inline_mapping_matches_only_known_sdk_packages(self):
        for name, runner in ((b'flutter', b'flutter'), (b'flutter_test', b'flutter'),
                             (b'other', b'dart'), (b'flutter_extra', b'dart')):
            with self.subTest(name=name):
                data = b'dependencies:\n  ' + name + b': {sdk: flutter}\n'
                self.assertEqual(self.select(data), [runner.decode(), 'test'])

    def test_unknown_package_after_valid_version_only_declaration(self):
        data = (b'dependencies:\n  flutter: any\n  unknown:\n'
                b'    sdk: flutter\n')
        self.assertEqual(self.select(data), ['dart', 'test'])


if __name__ == '__main__':
    unittest.main()
