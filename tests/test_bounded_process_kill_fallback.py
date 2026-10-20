"""Timeout cleanup should tolerate failures to signal POSIX process groups."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


@unittest.skipUnless(os.name == 'posix', 'POSIX process group signaling required')
class BoundedProcessKillFallbackTests(unittest.TestCase):
    def test_failed_process_group_signal_falls_back_to_child_kill(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('devpilot.bounded_process.os.killpg',
                       side_effect=PermissionError('private path should not leak')) as killpg:
                result = run_bounded(
                    [sys.executable, '-c', 'import time; time.sleep(60)'],
                    Path(temp), timeout=0.05,
                )
        killpg.assert_called_once()
        self.assertIsNone(result['exit_code'])
        self.assertEqual(result['error'], 'Timed out after 0.05s')
        self.assertFalse(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])
        self.assertNotIn('private', repr(result))

    def test_process_group_missing_race_does_not_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('devpilot.bounded_process.os.killpg',
                       side_effect=ProcessLookupError()) as killpg:
                result = run_bounded(
                    [sys.executable, '-c', 'import time; time.sleep(0.2)'],
                    Path(temp), timeout=0.02,
                )
        killpg.assert_called_once()
        self.assertIn('Timed out after', result['error'])


    def test_failed_group_and_child_kill_returns_failure_without_hanging(self):
        spawned = []
        real_popen = subprocess.Popen

        def launch(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            spawned.append(process)
            process.kill = lambda: (_ for _ in ()).throw(
                PermissionError('secret termination diagnostic')
            )
            return process

        try:
            with tempfile.TemporaryDirectory() as temp:
                with patch('devpilot.bounded_process.subprocess.Popen', side_effect=launch):
                    with patch('devpilot.bounded_process.os.killpg',
                               side_effect=PermissionError('private group')):
                        result = run_bounded(
                            [sys.executable, '-c', 'import time; time.sleep(60)'],
                            Path(temp), timeout=0.02,
                        )
            self.assertIn('unable to confirm process termination', result['error'])
            self.assertNotIn('secret', repr(result))
            self.assertNotIn('private', repr(result))
        finally:
            for process in spawned:
                real_popen.kill(process)
                process.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
