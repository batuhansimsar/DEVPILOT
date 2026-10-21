"""Elixir Mix project detection and guarded test selection."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import build_parser, main
from devpilot.core import analyze_project, detect_projects, doctor_report, test_commands
from devpilot.test_selection import ECOSYSTEMS, select_test_commands
from devpilot.workspaces import discover_workspaces


class ElixirProjectTests(unittest.TestCase):
    def test_root_mix_project_analyze_and_test_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'mix.exs').write_text('defmodule Demo.MixProject do\nend\n')
            (root / 'mix.lock').write_text('%{}\n')
            (root / 'lib').mkdir()
            (root / 'lib' / 'demo.ex').write_text('defmodule Demo do\nend\n')
            self.assertEqual(detect_projects(root), ['Elixir'])
            result = analyze_project(root)
            self.assertEqual(result['project_types'], ['Elixir'])
            self.assertEqual(result['languages'], {'Elixir': 2})
            self.assertIn('mix.exs', result['key_files'])
            self.assertIn('mix.lock', result['key_files'])
            self.assertEqual(test_commands(root), [
                {'ecosystem': 'Elixir', 'argv': ['mix', 'test'], 'reason': 'mix.exs'},
            ])

    def test_nested_mix_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / 'apps' / 'service'
            nested.mkdir(parents=True)
            (nested / 'mix.exs').touch()
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'apps/service')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Elixir'])

    def test_doctor_reports_missing_mix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'mix.exs').touch()
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertFalse(report['ok'])
            self.assertIn('Missing mix required by detected project', report['warnings'])

    def test_elixir_cli_filter_is_dry_run_by_default(self):
        self.assertEqual(ECOSYSTEMS['elixir'], 'Elixir')
        self.assertEqual(build_parser().parse_args(['test', '--ecosystem', 'elixir']).ecosystem, 'elixir')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'mix.exs').touch()
            (root / 'go.mod').write_text('module example.org/demo\n')
            commands = test_commands(root)
            self.assertEqual(select_test_commands(commands, 'elixir'), [
                {'ecosystem': 'Elixir', 'argv': ['mix', 'test'], 'reason': 'mix.exs'},
            ])
            output = io.StringIO()
            with patch('devpilot.cli.command_result', side_effect=AssertionError('must not execute')):
                with contextlib.redirect_stdout(output):
                    exit_code = main(['test', '--path', temporary, '--ecosystem', 'elixir', '--json'])
            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report['executed'])
            self.assertEqual([x['argv'] for x in report['commands']], [['mix', 'test']])

    def test_lock_only_backups_and_symlink_do_not_trigger_root_mix(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'mix.lock').touch()
            (root / 'mix.exs.bak').touch()
            self.assertNotIn('Elixir', detect_projects(root))
            self.assertEqual(test_commands(root), [])
            try:
                (root / 'mix.exs').symlink_to(root / 'mix.exs.bak')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Elixir', detect_projects(root))
            self.assertEqual(test_commands(root), [])


if __name__ == '__main__':
    unittest.main()
