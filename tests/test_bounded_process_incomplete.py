"""An apparently successful subprocess must not mask incomplete output capture."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

from devpilot.bounded_process import run_bounded


class IncompleteProcessCaptureTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'POSIX file-descriptor inheritance required')
    def test_inherited_pipes_report_capture_error_even_on_zero_exit(self):
        # A grandchild keeps both pipes open while its parent exits cleanly.
        # Redirect its standard streams to inherited pipes explicitly so the
        # test does not depend on platform-specific descriptor defaults.
        command = (
            'import subprocess, sys; '
            'subprocess.Popen([sys.executable, "-c", "import time; time.sleep(4)"], '
            'stdout=sys.stdout, stderr=sys.stderr); '
            'print("parent finished", flush=True)'
        )
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', command], Path(directory), timeout=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('parent finished', result['stdout'])
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])
        self.assertEqual(result['error'], 'Cannot capture complete command output')

    def test_successfully_drained_pipes_have_no_capture_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', 'print("done")'], Path(directory))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'done\n')
        self.assertNotIn('error', result)
