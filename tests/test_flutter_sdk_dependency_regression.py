"""Regression coverage for Flutter SDK packages and nested YAML fields."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class FlutterSdkDependencyRegressionTests(unittest.TestCase):
    def test_flutter_sdk_packages_choose_flutter_runner(self):
        for package in ('flutter', 'flutter_test', 'integration_test', 'flutter_localizations'):
            for sdk in ('flutter', '"flutter"', "'flutter'"):
                with self.subTest(package=package, sdk=sdk), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    (root / 'pubspec.yaml').write_text(
                        f'name: example\ndev_dependencies:\n  {package}:\n    sdk: {sdk}\n',
                        encoding='utf-8',
                    )
                    (root / 'test').mkdir()
                    self.assertEqual(dart_test_command(root, {'pubspec.yaml'})['argv'], ['flutter', 'test'])

    def test_nested_sdk_not_a_direct_dependency_attribute(self):
        manifests = (
            'dependencies:\n  example:\n    hosted:\n      sdk: flutter\n',
            'other:\n  example:\n    sdk: flutter\n',
            'dependencies:\n  example:\n    sdk: flutterish\n',
            '# dependencies:\n#   example:\n#     sdk: flutter\n',
        )
        for data in manifests:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'pubspec.yaml').write_text(data, encoding='utf-8')
                (root / 'test').mkdir()
                self.assertEqual(dart_test_command(root, {'pubspec.yaml'})['argv'], ['dart', 'test'])


if __name__ == '__main__':
    unittest.main()
