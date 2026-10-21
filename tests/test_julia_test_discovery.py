"""Regression tests for safe Julia test discovery and CLI selection."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import test_commands
from devpilot.test_selection import select_test_commands


class JuliaTestDiscoveryTests(unittest.TestCase):
    def test_requires_project_and_test_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            self.assertEqual(select_test_commands(test_commands(root), 'julia'), [])
            (root / 'JuliaProject.toml').touch()
            selected = select_test_commands(test_commands(root), 'julia')
            self.assertEqual([c['argv'] for c in selected],
                             [['julia', '--project=.', '-e', 'using Pkg; Pkg.test()']])
            (root / 'test' / 'runtests.jl').unlink()
            self.assertEqual(select_test_commands(test_commands(root), 'julia'), [])

    def test_rejects_symlinked_test_dir(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'Project.toml').touch()
            try:
                (root / 'test').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            (Path(external) / 'runtests.jl').touch()
            self.assertEqual(select_test_commands(test_commands(root), 'julia'), [])

    def test_cli_julia_only_dry_run_and_opt_in(self):
        from devpilot.cli import main, build_parser

        self.assertEqual(build_parser().parse_args(['test', '--ecosystem', 'julia']).ecosystem, 'julia')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Project.toml').touch()
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            (root / 'go.mod').touch()
            stdout = io.StringIO()
            with patch('devpilot.cli.command_result') as runner, contextlib.redirect_stdout(stdout):
                status = main(['test', '--path', directory, '--ecosystem', 'julia', '--json'])
            self.assertEqual(status, 0)
            self.assertEqual([c['ecosystem'] for c in json.loads(stdout.getvalue())['commands']], ['Julia'])
            runner.assert_not_called()
            stdout = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as runner, \
                    contextlib.redirect_stdout(stdout):
                status = main(['test', '--path', directory, '--ecosystem', 'julia', '--yes', '--json'])
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(stdout.getvalue())['executed'])
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0], ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'])


if __name__ == '__main__':
    unittest.main()
