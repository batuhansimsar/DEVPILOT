"""Keep root project diagnostics consistent with container workspace discovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.container_manifests import is_container_manifest
from devpilot.core import analyze_project, detect_projects, doctor_report
from devpilot.workspaces import discover_workspaces


class ContainerManifestTests(unittest.TestCase):
    def test_known_container_manifests(self):
        for filename in (
            'Dockerfile', 'Containerfile', 'Dockerfile.dev', 'Containerfile.prod',
            'compose.yml', 'compose.yaml', 'docker-compose.yml', 'docker-compose.yaml',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))

    def test_unrelated_names_not_classified(self):
        for filename in ('DockerfileX', 'myDockerfile.dev',
                         'ContainerfileOther', 'dockerfile', 'compose.json',
                         'docker-compose.yml.old'):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))

    def test_root_diagnostics_detect_named_containerfiles(self):
        for filename in ('Containerfile', 'Dockerfile.dev', 'Containerfile.prod'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / filename).write_text('FROM scratch\n', encoding='utf-8')
                self.assertEqual(detect_projects(root), ['Docker'])
                report = analyze_project(root)
                self.assertEqual(report['project_types'], ['Docker'])
                self.assertIn(filename, report['key_files'])
                with patch('devpilot.core.shutil.which', return_value=None):
                    health = doctor_report(root)
                self.assertIn('Docker', health['project_types'])
                self.assertIn('Missing docker required by detected project', health['warnings'])
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Docker'])

    def test_symlink_to_containerfile_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            target = Path(outside) / 'Dockerfile'
            target.write_text('FROM scratch\n', encoding='utf-8')
            try:
                (root / 'Dockerfile.dev').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(detect_projects(root), [])
            self.assertEqual(analyze_project(root)['key_files'], [])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
