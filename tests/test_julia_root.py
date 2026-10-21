"""Julia root reporting is consistent with monorepo inventory."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report
from devpilot.julia_manifests import is_julia_manifest
from devpilot.workspaces import discover_workspaces


class JuliaRootTests(unittest.TestCase):
    def test_regular_and_versioned_manifests(self):
        for manifest in ('Project.toml', 'JuliaProject.toml', 'Manifest.toml',
                         'JuliaManifest.toml', 'Manifest-v1.10.toml'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / manifest).touch()
                (root / 'app.jl').write_text('x = 1\n', encoding='utf-8')
                self.assertIn('Julia', detect_projects(root))
                report = analyze_project(root)
                self.assertIn(manifest, report['key_files'])
                self.assertEqual(report['languages'], {'Julia': 1})
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Julia'])

    def test_doctor_checks_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'Project.toml').touch()
            with patch('devpilot.core.shutil.which', return_value=None):
                self.assertIn('Missing julia required by detected project',
                              doctor_report(root)['warnings'])

    def test_malformed_names_and_symlinks_are_ignored(self):
        for name in ('Manifest-v01.10.toml', 'Manifest-v1.00.toml',
                     'Manifest-v1.toml', 'Manifest-v1.10.toml.bak', 'project.toml', None):
            self.assertFalse(is_julia_manifest(name))
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            target = Path(outside) / 'Project.toml'
            target.touch()
            try:
                (root / 'Project.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Julia', detect_projects(root))


if __name__ == '__main__':
    unittest.main()
