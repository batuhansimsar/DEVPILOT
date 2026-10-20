"""Regression tests for malicious tracked filenames in terminal diagnostics."""

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import main


@unittest.skipUnless(shutil.which('git'), 'Git executable required')
class TerminalSafetyTests(unittest.TestCase):
    def test_control_characters_are_escaped_in_human_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            hostile_name = 'nested/\x1b[31m\nserver.key'
            path = root / hostile_name
            path.parent.mkdir(parents=True)
            path.write_text('secret-content-must-not-appear', encoding='utf-8')
            subprocess.run(['git', 'add', '--', hostile_name], cwd=root, check=True, capture_output=True)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main([str(root)])
            self.assertEqual(exit_code, 1)
            self.assertNotIn('\x1b', output.getvalue())
            self.assertIn('\\u001b', output.getvalue())
            self.assertIn('\\nserver.key', output.getvalue())
            self.assertNotIn('secret-content-must-not-appear', output.getvalue())
            self.assertEqual(len(output.getvalue().splitlines()), 3)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([str(root), '--json']), 1)
            findings = json.loads(output.getvalue())['findings']
            self.assertEqual(findings[0]['path'], hostile_name)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([str(root), '--redact-paths']), 1)
            self.assertNotIn('server.key', output.getvalue())
            self.assertIn('<redacted>', output.getvalue())


if __name__ == '__main__':
    unittest.main()
