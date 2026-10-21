"""Ruby RSpec test plans are visible without execution and run only with --yes."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main
from devpilot.core import test_commands as discover_test_commands


class RubyCLIIntegrationTests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        (root / 'Gemfile').write_text("source 'https://rubygems.org'\n", encoding='utf-8')
        (root / 'spec').mkdir()
        (root / 'spec' / 'spec_helper.rb').write_text('', encoding='utf-8')

    def call_cli(self, argv: list[str]) -> tuple[int, dict]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(argv)
        return code, json.loads(out.getvalue())

    def test_core_detects_rspec_without_running_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            with patch('devpilot.core.command_result') as run:
                commands = discover_test_commands(root)
                run.assert_not_called()
        self.assertEqual([c['argv'] for c in commands], [['bundle', 'exec', 'rspec']])

    def test_cli_dry_run_works_with_ruby_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            self.make_project(Path(directory))
            with patch('devpilot.cli.command_result') as run:
                code, report = self.call_cli(['test', '--path', directory, '--ecosystem', 'ruby', '--json'])
                run.assert_not_called()
        self.assertEqual(code, 0)
        self.assertFalse(report['executed'])
        self.assertEqual(report['commands'][0]['argv'], ['bundle', 'exec', 'rspec'])

    def test_cli_yes_executes_selected_rspec_command(self):
        with tempfile.TemporaryDirectory() as directory:
            self.make_project(Path(directory))
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as run:
                code, report = self.call_cli(['test', '--path', directory, '--ecosystem', 'ruby', '--yes', '--json'])
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], ['bundle', 'exec', 'rspec'])
        self.assertEqual(code, 0)
        self.assertTrue(report['executed'])
        self.assertEqual(report['commands'][0]['result']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
