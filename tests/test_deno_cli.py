"""Regression tests for first-class Deno CLI support."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot import core
from devpilot.cli import main


class DenoCLITests(unittest.TestCase):
    def test_config_variants_are_detected_without_executing_them(self):
        for manifest in ('deno.json', 'deno.jsonc'):
            with self.subTest(manifest=manifest), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / manifest).write_text('{ invalid config }', encoding='utf-8')
                self.assertEqual(core.detect_projects(root), ['Deno'])
                self.assertIn(manifest, core.analyze_project(root)['key_files'])
                self.assertEqual(core.test_commands(root), [{
                    'ecosystem': 'Deno',
                    'argv': ['deno', 'test'],
                    'reason': 'Deno configuration',
                }])

    def test_doctor_reports_missing_deno_runtime(self):
        with TemporaryDirectory() as directory:
            (Path(directory) / 'deno.json').write_text('{}', encoding='utf-8')
            with patch('devpilot.core.shutil.which', return_value=None):
                report = core.doctor_report(Path(directory))
            self.assertFalse(report['ok'])
            self.assertIn('Missing deno required by detected project', report['warnings'])
            self.assertTrue(any(t['name'] == 'deno' and t['required_by'] == ['Deno']
                                for t in report['tools']))

    def test_deno_test_filter_is_dry_run_without_consent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'deno.json').write_text('{}', encoding='utf-8')
            (root / 'go.mod').write_text('module example.org/demo', encoding='utf-8')

            def invoke(flags):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    code = main(['test', '--path', directory, '--ecosystem', 'deno',
                                 '--json', *flags])
                return code, json.loads(stream.getvalue())

            with patch('devpilot.cli.command_result') as run:
                code, report = invoke([])
                self.assertEqual(code, 0)
                self.assertFalse(report['executed'])
                self.assertEqual([c['argv'] for c in report['commands']], [['deno', 'test']])
                run.assert_not_called()

            with patch('devpilot.cli.command_result', return_value={
                'exit_code': 0, 'stdout': '', 'stderr': '',
            }) as run:
                code, report = invoke(['--yes'])
                self.assertEqual(code, 0)
                self.assertTrue(report['executed'])
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0], ['deno', 'test'])


if __name__ == '__main__':
    unittest.main()
