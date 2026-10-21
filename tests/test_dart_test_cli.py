"""Dart test plans are discoverable and require --yes for execution."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import build_parser, main
from devpilot.core import test_commands
from devpilot.test_selection import select_test_commands


class DartTestCLIIntegrationTests(unittest.TestCase):
    def test_dry_run_filters_dart_from_other_projects(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').write_text('name: example\n', encoding='utf-8')
            (root / 'test').mkdir()
            (root / 'go.mod').touch()
            plan = test_commands(root)
            self.assertEqual(select_test_commands(plan, 'dart'), [{
                'ecosystem': 'Dart', 'argv': ['dart', 'test'],
                'reason': 'pubspec.yaml with test directory',
            }])
            output = io.StringIO()
            with patch('devpilot.cli.command_result') as runner, contextlib.redirect_stdout(output):
                code = main(['test', '--path', folder, '--ecosystem', 'dart', '--json'])
                runner.assert_not_called()
            report = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertFalse(report['executed'])
            self.assertEqual([x['ecosystem'] for x in report['commands']], ['Dart'])

    def test_dart_test_runs_only_with_yes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'pubspec.yaml').touch()
            (root / 'test').mkdir()
            output = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as runner, contextlib.redirect_stdout(output):
                code = main(['test', '--path', folder, '--ecosystem', 'dart', '--yes', '--json'])
                runner.assert_called_once()
                self.assertEqual(runner.call_args.args[0], ['dart', 'test'])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.getvalue())['executed'])

    def test_parser_exposes_dart_filter(self):
        self.assertEqual(build_parser().parse_args(
            ['test', '--ecosystem', 'dart']).ecosystem, 'dart')


if __name__ == '__main__':
    unittest.main()
