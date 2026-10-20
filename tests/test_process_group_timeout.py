"""Regression tests for bounded subprocess execution and timeout cleanup."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from devpilot.core import command_result


class CommandResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_preserves_output_and_exit_code(self):
        result = command_result(
            [sys.executable, '-c',
             'import sys; print("hello"); print("warning", file=sys.stderr); sys.exit(7)'],
            self.root,
        )
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(result['stdout'], 'hello\n')
        self.assertEqual(result['stderr'], 'warning\n')
        self.assertFalse(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])

    def test_missing_executable_is_reported(self):
        result = command_result(['devpilot-not-installed-sentinel-428103'], self.root)
        self.assertIsNone(result['exit_code'])
        self.assertIn('error', result)

    def test_large_output_is_bounded(self):
        result = command_result([sys.executable, '-c', 'print("x" * 21000)'], self.root)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(len(result['stdout']), 20000)
        self.assertTrue(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])

    @unittest.skipUnless(os.name == 'posix', 'process groups require POSIX')
    def test_timeout_kills_spawned_descendants(self):
        marker = self.root / 'escaped-child.txt'
        child_script = f'import time; time.sleep(1); open({str(marker)!r}, "w").write("survived")'
        parent_script = (
            'import subprocess, sys, time; '
            f'subprocess.Popen([sys.executable, "-c", {child_script!r}]); '
            'time.sleep(10)'
        )
        result = command_result([sys.executable, '-c', parent_script], self.root, timeout=0.4)
        self.assertIsNone(result['exit_code'])
        self.assertIn('Timed out', result['error'])
        time.sleep(1)
        self.assertFalse(marker.exists(), 'a timed-out test left a child process running')


if __name__ == '__main__':
    unittest.main()
