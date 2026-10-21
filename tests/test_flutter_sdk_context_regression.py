"""Regression coverage for Flutter SDK context and runner selection."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class FlutterSDKContextTests(unittest.TestCase):
    def plan(self, manifest: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text(manifest, encoding='utf-8')
            (root / 'test').mkdir()
            return dart_test_command(root, {'pubspec.yaml'})['argv']

    def test_other_flutter_sdk_dependencies_select_flutter(self):
        for package in ('flutter_test', 'flutter_localizations', 'integration_test'):
            with self.subTest(package=package):
                self.assertEqual(self.plan(
                    f'dev_dependencies:\n  {package}:\n    sdk: flutter\n'
                ), ['flutter', 'test'])

    def test_dependency_overrides_select_flutter(self):
        self.assertEqual(self.plan(
            'dependency_overrides:\n  flutter_test:\n    sdk: flutter\n'
        ), ['flutter', 'test'])

    def test_quoted_sdk_values_with_comments(self):
        for value in ("'flutter'", '"flutter"'):
            with self.subTest(value=value):
                self.assertEqual(self.plan(
                    f'dependencies: # packages\n  flutter: # sdk package\n    sdk: {value} # comment\n'
                ), ['flutter', 'test'])

    def test_quoted_package_names_select_flutter(self):
        for package in ("'flutter_test'", '"flutter_localizations"'):
            with self.subTest(package=package):
                self.assertEqual(self.plan(
                    f'dev_dependencies:\n  {package}:\n    sdk: flutter\n'
                ), ['flutter', 'test'])

    def test_unrelated_sdk_values_do_not_trigger_flutter(self):
        for manifest in (
            'sdk: flutter\n',
            'custom:\n  sdk: flutter\n',
            'description: |\n  dependencies:\n    flutter:\n      sdk: flutter\n',
            'dependencies:\n  example:\n    description: |\n      sdk: flutter\n',
            'dependencies:\n  flutter:\n    sdk: flutterish\n',
            'dependencies:\n  foo:\n    config:\n      sdk: flutter\n',
        ):
            with self.subTest(manifest=manifest):
                self.assertEqual(self.plan(manifest), ['dart', 'test'])

    def test_bom_and_crlf_remain_supported(self):
        self.assertEqual(self.plan(
            '\ufeffdependencies:\r\n  flutter:\r\n    sdk: flutter\r\n'
        ), ['flutter', 'test'])


if __name__ == '__main__':
    unittest.main()
