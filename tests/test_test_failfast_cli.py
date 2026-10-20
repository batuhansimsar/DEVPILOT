"""CLI-level regression for --fail-fast test execution."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main


class TestFailFastCliTests(unittest.TestCase):
    def test_json_marks_skipped_tests_and_does_not_execute_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"scripts":{"test":"echo test"}}')
            (root / 'go.mod').write_text('module example.com/demo')
            output = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 1}) as runner:
                with contextlib.redirect_stdout(output):
                    exit_code = main(['test', '--path', str(root), '--yes', '--fail-fast', '--json'])
            self.assertEqual(exit_code, 1)
            runner.assert_called_once()
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['commands']), 2)
            self.assertEqual(report['commands'][0]['result']['exit_code'], 1)
            self.assertNotIn('result', report['commands'][1])
            self.assertIn('fail-fast', report['commands'][1]['skipped_reason'])


if __name__ == '__main__':
    unittest.main()
