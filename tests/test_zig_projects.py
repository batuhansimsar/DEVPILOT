"""Root project and CLI support for Zig builds and package manifests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report, test_commands
from devpilot.test_selection import select_test_commands
from devpilot.workspaces import discover_workspaces


class ZigProjectTests(unittest.TestCase):
    def test_zig_build_detection_and_opt_in_test_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.zig').write_text('pub fn build() void {}\n')
            (root / 'build.zig.zon').write_text('.{}\n')
            (root / 'src').mkdir()
            (root / 'src' / 'main.zig').write_text('pub fn main() void {}\n')
            self.assertEqual(detect_projects(root), ['Zig'])
            report = analyze_project(root)
            self.assertEqual(report['languages'], {'Zig': 2})
            self.assertIn('build.zig', report['key_files'])
            self.assertIn('build.zig.zon', report['key_files'])
            commands = test_commands(root)
            self.assertEqual(commands, [
                {'ecosystem': 'Zig', 'argv': ['zig', 'build', 'test'], 'reason': 'build.zig'},
            ])
            self.assertEqual(select_test_commands(commands, 'zig'), commands)
            self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Zig'])

    def test_zon_only_detected_but_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.zig.zon').write_text('.{}\n')
            self.assertEqual(detect_projects(root), ['Zig'])
            self.assertEqual(test_commands(root), [])

    def test_doctor_checks_zig_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.zig').write_text('')
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Missing zig required by detected project', report['warnings'])
            self.assertFalse(report['ok'])

    def test_symlink_and_backup_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.zig.bak').write_text('')
            self.assertNotIn('Zig', detect_projects(root))
            try:
                (root / 'build.zig').symlink_to(root / 'build.zig.bak')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Zig', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
