"""R and RStudio project discovery is consistent across read-only commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core
from devpilot.r_manifests import is_r_manifest
from devpilot.workspaces import discover_workspaces


class RProjectDetectionTests(unittest.TestCase):
    def test_filename_validation(self):
        for name in ('renv.lock', 'my-analysis.Rproj', 'a.b.Rproj', 'Research 2026.Rproj'):
            with self.subTest(name=name):
                self.assertTrue(is_r_manifest(name))
        for name in ('.Rproj', '.hidden.Rproj', 'renv.lock.bak', 'renv.LOCK',
                     'project.Rproj~', 'project.Rproj.bak', 'project.rproj',
                     'folder/project.Rproj', r'folder\project.Rproj',
                     'bad\nname.Rproj', 'README.md', '', None, 123):
            with self.subTest(name=name):
                self.assertFalse(is_r_manifest(name))

    def test_root_analysis_workspace_and_doctor(self):
        for manifest in ('renv.lock', 'experiment.Rproj'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / manifest).write_text('', encoding='utf-8')
                (root / 'model.R').write_text('x <- 1\n', encoding='utf-8')
                (root / 'report.Rmd').write_text('---\n', encoding='utf-8')
                self.assertEqual(core.detect_projects(root), ['R'])
                report = core.analyze_project(root)
                self.assertIn(manifest, report['key_files'])
                self.assertEqual(report['languages'], {'R': 2})
                spaces = discover_workspaces(root)
                self.assertEqual(spaces['workspace_count'], 1)
                self.assertEqual(spaces['workspaces'][0]['ecosystems'], ['R'])
                self.assertEqual(spaces['workspaces'][0]['manifests'], [
                    {'file': manifest, 'ecosystem': 'R'}])
                with patch('devpilot.core.shutil.which', return_value=None):
                    doctor = core.doctor_report(root)
                self.assertIn('Missing Rscript required by detected project', doctor['warnings'])
                # No universal R test runner can be inferred from a project marker.
                self.assertEqual(core.test_commands(root), [])

    def test_nested_workspaces_and_unrelated_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'renv.lock.bak').touch()
            (root / 'foo.rproj').touch()
            nested = root / 'apps' / 'statistics'
            nested.mkdir(parents=True)
            (nested / 'statistics.Rproj').touch()
            self.assertEqual(core.detect_projects(root), [])
            spaces = discover_workspaces(root)
            self.assertEqual(spaces['workspace_count'], 1)
            self.assertEqual(spaces['workspaces'][0]['path'], 'apps/statistics')
            self.assertEqual(spaces['workspaces'][0]['ecosystems'], ['R'])

    def test_symlinked_manifest_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'linked.Rproj'
            target.touch()
            try:
                (root / 'linked.Rproj').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(core.detect_projects(root), [])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)
            self.assertNotIn('linked.Rproj', core.analyze_project(root)['key_files'])


if __name__ == '__main__':
    unittest.main()
