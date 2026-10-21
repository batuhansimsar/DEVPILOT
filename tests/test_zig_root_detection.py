"""Zig roots are recognized consistently by analyze, doctor and workspaces."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core
from devpilot.workspaces import discover_workspaces


class ZigRootDetectionTests(unittest.TestCase):
    def test_zig_manifest_variants_are_recognized_without_running_project_code(self):
        for manifest in ('build.zig', 'build.zig.zon'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / manifest).write_text('', encoding='utf-8')
                analysis = core.analyze_project(root)
                self.assertEqual(analysis['project_types'], ['Zig'])
                self.assertIn(manifest, analysis['key_files'])
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Zig'])
                self.assertFalse(any(command['ecosystem'] == 'Zig'
                                     for command in core.test_commands(root)))
                with patch('devpilot.core.shutil.which', return_value=None):
                    doctor = core.doctor_report(root)
                self.assertIn('Missing zig required by detected project', doctor['warnings'])
                self.assertFalse(doctor['ok'])

    def test_backups_are_not_zig_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('build.zig.bak', 'build.zig.zon.old', 'README.md'):
                (root / name).write_text('', encoding='utf-8')
            self.assertNotIn('Zig', core.detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_symlinked_manifest_is_not_counted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'build.zig'
            target.write_text('', encoding='utf-8')
            try:
                (root / 'build.zig').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('Zig', core.detect_projects(root))
            self.assertNotIn('build.zig', core.analyze_project(root)['key_files'])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
