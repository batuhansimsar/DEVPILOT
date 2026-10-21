"""Flutter discovery handles YAML-quoted dependency names and SDK keys."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class QuotedDependencyKeysTests(unittest.TestCase):
    def test_quoted_sections_packages_and_sdk_keys(self):
        for section in ('dependencies', '"dependencies"', "'dev_dependencies'", '"dependency_overrides"'):
            for package in ('flutter', '"flutter"', "'flutter_test'", '"flutter_driver" '):
                for sdk_key in ('sdk', '"sdk"', "'sdk'"):
                    with self.subTest(section=section, package=package, sdk=sdk_key), tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp)
                        (root / 'test').mkdir()
                        (root / 'pubspec.yaml').write_text(
                            f'name: example\n{section}:\n  {package}: # SDK dependency\n    {sdk_key}: flutter\n',
                            encoding='utf-8',
                        )
                        self.assertEqual(
                            dart_test_command(root, {'pubspec.yaml'})['argv'], ['flutter', 'test']
                        )

    def test_unrelated_or_nested_keys_do_not_trigger_flutter(self):
        for pubspec in (
            '"other_dependencies":\n  "flutter":\n    sdk: flutter\n',
            'other:\n  "dependencies":\n    "flutter":\n      sdk: flutter\n',
            'dependencies:\n  "not-a-valid-package":\n    sdk: flutter\n',
            'dependencies:\n  "flutter":\n    sdk: hosted\n',
            'dependencies:\n  # "flutter":\n  unrelated: any\n',
            'dependencies:\n  "flutter":\n    "not_sdk": flutter\n',
        ):
            with self.subTest(pubspec=pubspec), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'test').mkdir()
                (root / 'pubspec.yaml').write_text('name: example\n' + pubspec, encoding='utf-8')
                self.assertEqual(
                    dart_test_command(root, {'pubspec.yaml'})['argv'], ['dart', 'test']
                )


if __name__ == '__main__':
    unittest.main()
