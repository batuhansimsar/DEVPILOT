"""Pipes still held open after process exit must be reported as incomplete."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

from devpilot.bounded_process import run_bounded


@unittest.skipUnless(os.name == 'posix', 'POSIX pipe inheritance required')
class IncompleteOutputTests(unittest.TestCase):
    def test_descendant_holding_both_pipes_marks_output_incomplete(self):
        # The direct child exits successfully, but its descendant holds both
        # pipes for longer than the bounded reader joins. No output is lost
        # silently: clients can reject a potentially incomplete result.
        code = (
            'import subprocess, sys; '
            'subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"], '
            'stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.DEVNULL); '
            'print("parent complete", flush=True)'
        )
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', code], Path(directory), timeout=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('parent complete', result['stdout'])
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])

    def test_completed_pipes_remain_untruncated(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', 'print("done")'], Path(directory), timeout=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])


if __name__ == '__main__':
    unittest.main()
