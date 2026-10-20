import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main


class CliTests(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(args)
        return code, output.getvalue()

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'go.mod').write_text('module x')
            code, text = self.call(['analyze', '--path', directory, '--json'])
            self.assertEqual(code, 0)
            self.assertIn('Go', json.loads(text)['project_types'])

    def test_doctor_json_nonzero_when_project_dependency_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'go.mod').write_text('module x')
            with patch('devpilot.core.shutil.which', return_value=None):
                code, text = self.call(['doctor', '--path', directory, '--json'])
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(text)['ok'])

    def test_test_execution_requires_yes(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'package.json').write_text('{"scripts":{"test":"echo okay"}}')
            with patch('devpilot.cli.command_result') as run:
                code, output = self.call(['test', '--path', directory])
                run.assert_not_called()
            self.assertEqual(code, 0)
            self.assertIn('dry run', output)

    def test_test_yes_checks_results(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'package.json').write_text('{"scripts":{"test":"exit 1"}}')
            with patch('devpilot.cli.command_result', return_value={'exit_code': 5, 'stdout': '', 'stderr': 'failed'}) as run:
                code, _ = self.call(['test', '--path', directory, '--yes', '--json'])
                run.assert_called_once()
            self.assertEqual(code, 1)

    def test_test_ecosystem_filters_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'go.mod').write_text('module example.com/demo')
            (path / 'package.json').write_text('{"scripts":{"test":"exit 1"}}')
            result = {'exit_code': 0, 'stdout': '', 'stderr': ''}
            with patch('devpilot.cli.command_result', return_value=result) as run:
                code, output = self.call(['test', '--path', directory, '--ecosystem', 'go', '--yes', '--json'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)['commands'][0]['argv'], ['go', 'test', './...'])
            self.assertEqual(len(json.loads(output)['commands']), 1)
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ['go', 'test', './...'])

    def test_test_ecosystem_without_match_does_not_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'go.mod').write_text('module example.com/demo')
            with patch('devpilot.cli.command_result') as run:
                code, output = self.call(['test', '--path', directory, '--ecosystem', 'python', '--yes', '--json'])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output)['commands'], [])
            run.assert_not_called()

    def test_empty_test_returns_1(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output = self.call(['test', '--path', directory])
        self.assertEqual(code, 1)
        self.assertIn('No supported', output)

    def test_tcp_port_validation(self):
        with self.assertRaises(SystemExit):
            self.call(['check', 'localhost', '65536'])


if __name__ == '__main__':
    unittest.main()
