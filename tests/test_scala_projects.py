"""Regression tests for Scala/SBT detection across repository commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report, test_commands
from devpilot.workspaces import discover_workspaces


class ScalaProjectTests(unittest.TestCase):
    def test_root_sbt_project_is_discovered_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('scalaVersion := "3.6.2"\n')
            (root / 'Main.scala').write_text('object Main {}\n')
            self.assertEqual(detect_projects(root), ['Scala'])
            analysis = analyze_project(root)
            self.assertEqual(analysis['project_types'], ['Scala'])
            self.assertEqual(analysis['languages'], {'Scala': 2})
            self.assertIn('build.sbt', analysis['key_files'])
            self.assertEqual(test_commands(root), [
                {'ecosystem': 'Scala', 'argv': ['sbt', 'test'], 'reason': 'build.sbt'},
            ])

    def test_nested_sbt_workspace_is_recognized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'modules' / 'library'
            nested.mkdir(parents=True)
            (nested / 'build.sbt').write_text('name := "library"\n')
            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 1)
            self.assertEqual(result['workspaces'][0]['path'], 'modules/library')
            self.assertEqual(result['workspaces'][0]['ecosystems'], ['Scala'])
            self.assertEqual(result['workspaces'][0]['manifests'], [
                {'file': 'build.sbt', 'ecosystem': 'Scala'},
            ])

    def test_doctor_reports_missing_sbt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('name := "demo"\n')
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Scala', report['project_types'])
            self.assertIn('Missing sbt required by detected project', report['warnings'])
            self.assertFalse(report['ok'])

    def test_unrelated_or_symlinked_build_files_are_not_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt.bak').write_text('not a build')
            (root / 'project').mkdir()
            (root / 'project' / 'build.properties').write_text('sbt.version=1.10.0')
            self.assertNotIn('Scala', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)
            try:
                (root / 'build.sbt').symlink_to(root / 'build.sbt.bak')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Scala', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
