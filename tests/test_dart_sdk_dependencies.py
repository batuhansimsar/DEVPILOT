"""Regression tests for Flutter SDK detection in pubspec.yaml."""

import tempfile
import unittest
from pathlib import Path

from devpilot.dart_tests import dart_test_command


class FlutterSDKDependencyTests(unittest.TestCase):
    def _command(self, manifest: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pubspec.yaml').write_text(manifest, encoding='utf-8')
            (root / 'test').mkdir()
            return dart_test_command(root, {'pubspec.yaml'})['argv']

    def test_flutter_sdk_dependencies(self):
        for section in ('dependencies', 'dev_dependencies', 'dependency_overrides'):
            for sdk in ('flutter', "'flutter'", '"flutter"'):
                with self.subTest(section=section, sdk=sdk):
                    self.assertEqual(self._command(f'{section}:\n  flutter:\n    sdk: {sdk} # comment\n'),
                                     ['flutter', 'test'])

    def test_unrelated_sdk_or_nested_flutter_is_not_flutter_project(self):
        for manifest in (
            'environment:\n  sdk: flutter\n',
            'description: |\n  sdk: flutter\n',
            'dependencies:\n  other:\n    flutter:\n      sdk: flutter\n',
            'dependencies:\n  something:\n    sdk: flutter\n',
            'dependencies:\n  flutter:\n    description: |\n      sdk: flutter\n',
            'dependencies:\n  flutter: any\n  other:\n    sdk: flutter\n',
            '# dependencies:\n#   flutter:\n#     sdk: flutter\n',
        ):
            with self.subTest(manifest=manifest):
                self.assertEqual(self._command(manifest), ['dart', 'test'])

    def test_sibling_dependency_and_top_level_section_boundaries(self):
        manifest = ('dependencies:\n  flutter:\n    sdk: hosted\n  other:\n    sdk: flutter\n'
                    'environment:\n  sdk: flutter\n')
        self.assertEqual(self._command(manifest), ['dart', 'test'])

    def test_bom_and_blank_or_comment_lines(self):
        manifest = '\ufeffdependencies:\n\n  # SDK source\n  flutter:\n\n    # comment\n    sdk: flutter\n'
        self.assertEqual(self._command(manifest), ['flutter', 'test'])


if __name__ == '__main__':
    unittest.main()
