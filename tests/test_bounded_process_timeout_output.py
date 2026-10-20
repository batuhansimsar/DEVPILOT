"""Regression coverage for diagnostic output from timed-out commands."""

import sys
import tempfile
import unittest
from pathlib import Path

from devpilot.bounded_process import MAX_OUTPUT_BYTES, run_bounded


class TimedOutOutputTests(unittest.TestCase):
    def test_timeout_preserves_bounded_stdout_and_stderr(self):
        script = (
            "import os, time; "
            "os.write(1, b'a'*30000 + b'STDOUT-END'); "
            "os.write(2, b'b'*30000 + b'STDERR-END'); "
            "time.sleep(10)"
        )
        with tempfile.TemporaryDirectory() as folder:
            result = run_bounded([sys.executable, '-c', script], Path(folder), timeout=2)

        self.assertIsNone(result['exit_code'])
        self.assertIn('Timed out', result['error'])
        self.assertTrue(result['stdout'].endswith('STDOUT-END'))
        self.assertTrue(result['stderr'].endswith('STDERR-END'))
        self.assertEqual(len(result['stdout']), MAX_OUTPUT_BYTES)
        self.assertEqual(len(result['stderr']), MAX_OUTPUT_BYTES)
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])


if __name__ == '__main__':
    unittest.main()
