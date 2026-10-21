"""Consistent, read-only detection of Conda and Pixi workspace markers."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report
from devpilot.workspaces import discover_workspaces


class CondaPixiDiscoveryTests(unittest.TestCase):
    def test_root_pixi_manifest_and_nested_lockfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pixi.toml').write_text('[workspace]\n')
            nested = root / 'apps' / 'worker'
            nested.mkdir(parents=True)
            (nested / 'pixi.lock').write_text('version: 6\n')

            self.assertEqual(detect_projects(root), ['Conda'])
            analysis = analyze_project(root)
            self.assertIn('pixi.toml', analysis['key_files'])
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 2)
            self.assertEqual(
                [(workspace['path'], workspace['ecosystems']) for workspace in report['workspaces']],
                [('.', ['Conda']), ('apps/worker', ['Conda'])],
            )
            self.assertEqual(report['workspaces'][1]['manifests'],
                             [{'file': 'pixi.lock', 'ecosystem': 'Conda'}])

    def test_conda_environment_markers_are_consistent(self):
        for name in ('environment.yml', 'environment.yaml'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('name: example\n')
                self.assertEqual(detect_projects(root), ['Conda'])
                self.assertIn(name, analyze_project(root)['key_files'])
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Conda'])

    def test_doctor_uses_pixi_for_pixi_projects_and_conda_for_environments(self):
        for filename, executable in (('pixi.lock', 'pixi'), ('environment.yml', 'conda')):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).touch()
                with patch('devpilot.core.shutil.which', return_value=None):
                    report = doctor_report(root)
                self.assertIn('Conda', report['project_types'])
                self.assertIn(f'Missing {executable} required by detected project', report['warnings'])
                tool = next(tool for tool in report['tools'] if tool['name'] == executable)
                self.assertEqual(tool['required_by'], ['Conda'])

    def test_symlinked_pixi_manifest_is_not_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            try:
                (root / 'pixi.toml').symlink_to('missing-pixi.toml')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('Conda', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
