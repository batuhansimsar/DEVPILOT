"""Regression tests for Scala/SBT test filtering."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import contextlib
import io
import json

from devpilot.cli import build_parser, main
from devpilot.test_selection import ECOSYSTEMS, select_test_commands


class ScalaTestFilterTests(unittest.TestCase):
    def test_scala_is_accepted_by_cli_parser(self):
        self.assertEqual(ECOSYSTEMS['scala'], 'Scala')
        parsed = build_parser().parse_args(['test', '--ecosystem', 'scala'])
        self.assertEqual(parsed.ecosystem, 'scala')

    def test_selection_keeps_only_scala_without_mutating_discovery(self):
        commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': 'Scala', 'argv': ['sbt', 'test']},
            {'ecosystem': 'Java', 'argv': ['mvn', 'test']},
        ]
        selected = select_test_commands(commands, 'scala')
        self.assertEqual(selected, [commands[1]])
        selected[0]['argv'].append('--offline')
        self.assertEqual(commands[1]['argv'], ['sbt', 'test'])
        self.assertEqual(select_test_commands(commands, 'go'), [commands[0]])

    def test_cli_dry_run_does_not_execute_other_ecosystems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('name := "sample"\n')
            (root / 'go.mod').write_text('module example.org/sample\n')
            output = io.StringIO()
            with patch('devpilot.cli.command_result') as run:
                with contextlib.redirect_stdout(output):
                    code = main(['test', '--path', directory, '--ecosystem', 'scala', '--json'])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report['executed'])
            self.assertEqual([entry['argv'] for entry in report['commands']], [['sbt', 'test']])
            run.assert_not_called()

    def test_cli_executes_only_selected_scala_command_with_yes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build.sbt').write_text('name := "sample"\n')
            (root / 'go.mod').write_text('module example.org/sample\n')
            output = io.StringIO()
            with patch('devpilot.cli.command_result',
                       return_value={'exit_code': 0, 'stdout': '', 'stderr': ''}) as run:
                with contextlib.redirect_stdout(output):
                    code = main(['test', '--path', directory, '--ecosystem', 'scala', '--yes', '--json'])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertTrue(report['executed'])
            self.assertEqual(len(report['commands']), 1)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ['sbt', 'test'])


if __name__ == '__main__':
    unittest.main()
