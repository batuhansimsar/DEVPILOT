"""Swift Package Manager detection, test discovery and CLI filtering."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import build_parser, main
from devpilot.core import analyze_project, detect_projects, doctor_report, test_commands
from devpilot.workspaces import discover_workspaces


class SwiftPackageTests(unittest.TestCase):
    def test_root_manifest_detects_swift_and_discovers_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Package.swift').write_text('// swift-tools-version: 5.9\n')
            (root / 'Package.resolved').write_text('{}\n')
            (root / 'main.swift').write_text('print("hello")\n')
            self.assertEqual(detect_projects(root), ['Swift'])
            report = analyze_project(root)
            self.assertEqual(report['project_types'], ['Swift'])
            self.assertIn('Package.swift', report['key_files'])
            self.assertIn('Package.resolved', report['key_files'])
            self.assertEqual(report['languages'], {'Swift': 2})
            self.assertEqual(test_commands(root), [
                {'ecosystem': 'Swift', 'argv': ['swift', 'test'], 'reason': 'Package.swift'},
            ])

    def test_swift_package_is_found_in_nested_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'packages' / 'backend'
            nested.mkdir(parents=True)
            (nested / 'Package.swift').write_text('// manifest\n')
            workspaces = discover_workspaces(root)
            self.assertEqual(workspaces['workspace_count'], 1)
            self.assertEqual(workspaces['workspaces'][0]['path'], 'packages/backend')
            self.assertEqual(workspaces['workspaces'][0]['ecosystems'], ['Swift'])

    def test_doctor_reports_missing_swift_compiler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Package.swift').write_text('// manifest\n')
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Missing swift required by detected project', report['warnings'])
            self.assertFalse(report['ok'])

    def test_manifest_backups_and_symlinks_do_not_trigger_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Package.swift.bak').write_text('// not a manifest\n')
            (root / 'Package.resolved').write_text('{}')
            self.assertEqual(detect_projects(root), [])
            self.assertEqual(test_commands(root), [])
            try:
                (root / 'Package.swift').symlink_to(root / 'Package.swift.bak')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(detect_projects(root), [])
            self.assertEqual(test_commands(root), [])

    def test_cli_filters_swift_tests_and_requires_opt_in_to_execute(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(['test', '--ecosystem', 'swift']).ecosystem, 'swift')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Package.swift').write_text('// manifest\n')
            (root / 'go.mod').write_text('module example.org/demo\n')
            output = io.StringIO()
            with patch('devpilot.cli.command_result') as run, contextlib.redirect_stdout(output):
                code = main(['test', '--path', directory, '--ecosystem', 'swift', '--json'])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report['executed'])
            self.assertEqual([entry['argv'] for entry in report['commands']], [['swift', 'test']])
            run.assert_not_called()
            output = io.StringIO()
            with patch('devpilot.cli.command_result',
                       return_value={'exit_code': 0, 'stdout': '', 'stderr': ''}) as run, contextlib.redirect_stdout(output):
                code = main(['test', '--path', directory, '--ecosystem', 'swift', '--yes', '--json'])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.getvalue())['executed'])
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ['swift', 'test'])


if __name__ == '__main__':
    unittest.main()
