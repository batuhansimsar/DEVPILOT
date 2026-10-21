"""Regression tests: repository scans must not resolve away linked roots."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main
from devpilot.core import analyze_project


class ScanRootIntegrationTests(unittest.TestCase):
    def _linked_project(self, parent: Path) -> tuple[Path, Path]:
        target = parent / 'target'
        target.mkdir()
        (target / 'go.mod').write_text('module private.example/project\n')
        (target / 'package.json').write_text('{"scripts":{"test":"private-command"}}')
        alias = parent / 'alias'
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        return alias, target

    def test_analyze_does_not_inspect_linked_root_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            alias, _ = self._linked_project(Path(directory))
            with patch('devpilot.core._read_package_json') as reader:
                report = analyze_project(alias)
            reader.assert_not_called()
            self.assertTrue(report['truncated'])
            self.assertEqual(report['project_types'], [])
            self.assertEqual(report['npm_scripts'], [])
            self.assertEqual(report['file_count'], 0)
            self.assertIn('symbolic link', report['problems'][0])
            self.assertNotIn(str(alias), report['problems'][0])

    def test_analyze_rejects_linked_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            alias, target = self._linked_project(Path(directory))
            (target / 'nested').mkdir()
            report = analyze_project(alias / 'nested')
            self.assertTrue(report['truncated'])
            self.assertEqual(report['project_types'], [])
            self.assertIn('symbolic link', report['problems'][0])

    def test_cli_analyze_and_workspaces_reject_symlink_root(self):
        with tempfile.TemporaryDirectory() as directory:
            alias, _ = self._linked_project(Path(directory))
            for command in ('analyze', 'workspaces'):
                with self.subTest(command=command):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main([command, '--path', str(alias), '--json'])
                    report = json.loads(output.getvalue())
                    self.assertEqual(status, 1)
                    self.assertTrue(report['truncated'])
                    self.assertTrue(report['problems'])
                    self.assertNotIn('private.example', output.getvalue())
                    if command == 'workspaces':
                        self.assertEqual(report['workspace_count'], 0)
                    else:
                        self.assertEqual(report['project_types'], [])


if __name__ == '__main__':
    unittest.main()
