"""CLI ecosystem filters must accept case variants without running project code."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.cli import build_parser, main
from devpilot.core import test_commands as discover_test_commands
from devpilot.test_selection import ECOSYSTEMS, select_test_commands


class HaskellTestFilterTests(unittest.TestCase):
    def test_filter_preserves_independent_command_plan(self):
        commands = [
            {'ecosystem': 'Haskell', 'argv': ['stack', 'test'], 'reason': 'stack.yaml'},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'},
        ]
        self.assertEqual(ECOSYSTEMS['haskell'], 'Haskell')
        selected = select_test_commands(commands, 'HaSkElL')
        self.assertEqual(selected, commands[:1])
        selected[0]['argv'].append('--flag')
        self.assertEqual(commands[0]['argv'], ['stack', 'test'])

    def test_case_insensitive_cli_filter_for_stack_and_cabal(self):
        for manifest, expected in [('stack.yaml', ['stack', 'test']),
                                   ('library.cabal', ['cabal', 'test'])]:
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / manifest).write_text('', encoding='utf-8')
                self.assertEqual(discover_test_commands(root)[0]['argv'], expected)
                args = ['test', '--path', str(root), '--ecosystem', 'HaSkElL', '--json']
                self.assertEqual(build_parser().parse_args(args).ecosystem, 'haskell')
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    status = main(args)
                self.assertEqual(status, 0)
                report = json.loads(stdout.getvalue())
                self.assertFalse(report['executed'])
                self.assertEqual([item['argv'] for item in report['commands']], [expected])
                self.assertEqual(report['commands'][0]['ecosystem'], 'Haskell')

    def test_case_insensitive_go_filter_excludes_other_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'go.mod').write_text('module example.org/test\\n', encoding='utf-8')
            (root / 'stack.yaml').write_text('', encoding='utf-8')
            args = ['test', '--path', str(root), '--ecosystem', 'GO', '--json']
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(args)
            self.assertEqual(status, 0)
            report = json.loads(stdout.getvalue())
            self.assertFalse(report['executed'])
            self.assertEqual([item['ecosystem'] for item in report['commands']], ['Go'])
            self.assertEqual(report['commands'][0]['argv'], ['go', 'test', './...'])


if __name__ == '__main__':
    unittest.main()
