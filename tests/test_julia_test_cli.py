"""Julia test plans are selectable without running code until --yes."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main
from devpilot.core import test_commands


class JuliaCLIIntegrationTests(unittest.TestCase):
    def test_core_discovers_julia_pkg_test_from_project_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Project.toml').write_text('name = "Example"\n', encoding='utf-8')
            with patch('devpilot.core.command_result') as run:
                commands = test_commands(root)
                run.assert_not_called()
        self.assertEqual([command['argv'] for command in commands], [
            ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
        ])

    def test_cli_dry_run_filters_julia_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'JuliaProject.toml').touch()
            output = io.StringIO()
            with patch('devpilot.cli.command_result') as run, contextlib.redirect_stdout(output):
                code = main(['test', '--path', directory, '--ecosystem', 'julia', '--json'])
                run.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertFalse(report['executed'])
        self.assertEqual(report['commands'][0]['ecosystem'], 'Julia')

    def test_cli_yes_executes_only_selected_julia_command(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'Project.toml').touch()
            (Path(directory) / 'go.mod').touch()
            output = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as run, contextlib.redirect_stdout(output):
                code = main(['test', '--path', directory, '--ecosystem', 'julia', '--yes', '--json'])
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], [
                    'julia', '--project=.', '-e', 'using Pkg; Pkg.test()',
                ])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(report['executed'])
        self.assertEqual(len(report['commands']), 1)


if __name__ == '__main__':
    unittest.main()
