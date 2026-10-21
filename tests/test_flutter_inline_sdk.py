"""Inline Flutter SDK dependency maps select the correct test runner."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.dart_tests import dart_test_command


class InlineFlutterSDKTests(unittest.TestCase):
    def _runner(self, manifest: bytes) -> list[str]:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_bytes(manifest)
            (root / 'test').mkdir()
            return dart_test_command(root, {'pubspec.yaml'})['argv']

    def test_inline_flutter_mapping_variants(self):
        for value in (b'flutter', b'"flutter"', b"'flutter'"):
            for section in (b'dependencies', b'dev_dependencies', b'dependency_overrides'):
                with self.subTest(value=value, section=section):
                    content = b'name: example\n' + section + b':\n  flutter: { sdk: ' + value + b' } # SDK\n'
                    self.assertEqual(self._runner(content), ['flutter', 'test'])

    def test_quoted_dependency_and_sdk_keys(self):
        for dependency in (b'flutter', b'"flutter"', b"'flutter'"):
            for key in (b'sdk', b'"sdk"', b"'sdk'"):
                with self.subTest(dependency=dependency, key=key):
                    content = b'dependencies:\n  ' + dependency + b': {' + key + b': flutter}\n'
                    self.assertEqual(self._runner(content), ['flutter', 'test'])

    def test_near_matches_remain_plain_dart(self):
        for value in (
            b'name: example\n# dependencies:\n#   flutter: {sdk: flutter}\n',
            b'name: example\ndependencies:\n  other: {sdk: flutter}\n',
            b'name: example\ndependencies:\n  flutter: {sdk: flutterish}\n',
            b'name: example\ndependencies:\n  flutter: {sdk: flutter, typo: 1}\n',
            b'name: example\ntools:\n  flutter: {sdk: flutter}\n',
        ):
            with self.subTest(value=value):
                self.assertEqual(self._runner(value), ['dart', 'test'])


if __name__ == '__main__':
    unittest.main()
