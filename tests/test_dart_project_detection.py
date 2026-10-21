"""Keep Dart root analysis and workspace discovery in sync."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core
from devpilot.workspaces import discover_workspaces


class DartProjectDetectionTests(unittest.TestCase):
    def test_pubspec_yaml_and_lockfile_only_roots(self):
        for marker in ('pubspec.yaml', 'pubspec.lock'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / marker).write_text('', encoding='utf-8')
                analysis = core.analyze_project(root)
                self.assertEqual(analysis['project_types'], ['Dart'])
                self.assertIn(marker, analysis['key_files'])
                workspaces = discover_workspaces(root)
                self.assertEqual(workspaces['workspaces'][0]['ecosystems'], ['Dart'])
                with patch('devpilot.core.shutil.which', return_value=None):
                    doctor = core.doctor_report(root)
                self.assertIn('Missing dart required by detected project', doctor['warnings'])

    def test_both_manifests_report_one_project_type(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for marker in ('pubspec.yaml', 'pubspec.lock'):
                (root / marker).write_text('', encoding='utf-8')
            analysis = core.analyze_project(root)
            self.assertEqual(analysis['project_types'], ['Dart'])
            self.assertTrue({'pubspec.yaml', 'pubspec.lock'} <= set(analysis['key_files']))
            self.assertEqual(core.test_commands(root), [])

    def test_unrelated_and_symlinked_pubspec_are_not_detected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'pubspec.yaml.bak').write_text('', encoding='utf-8')
            (Path(external) / 'pubspec.yaml').write_text('', encoding='utf-8')
            try:
                (root / 'pubspec.yaml').symlink_to(Path(external) / 'pubspec.yaml')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('Dart', core.detect_projects(root))
            self.assertEqual(core.analyze_project(root)['key_files'], [])


if __name__ == '__main__':
    unittest.main()
