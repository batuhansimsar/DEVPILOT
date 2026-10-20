"""Reject deadlines that overflow the platform's process wait machinery."""

import sys
import tempfile
import unittest
from pathlib import Path
from threading import TIMEOUT_MAX
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


class BoundedProcessTimeoutCeilingTests(unittest.TestCase):
    def test_platform_oversized_deadline_never_spawns_child(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.bounded_process.subprocess.Popen') as launch:
                result = run_bounded([sys.executable, '-c', 'print("not executed")'],
                                     Path(directory), timeout=TIMEOUT_MAX * 2)
            launch.assert_not_called()
        self.assertIsNone(result['exit_code'])
        self.assertIn('platform limit', result['error'])

    def test_short_finite_timeout_still_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', 'print("ready")'],
                                 Path(directory), timeout=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ready\n')


if __name__ == '__main__':
    unittest.main()
