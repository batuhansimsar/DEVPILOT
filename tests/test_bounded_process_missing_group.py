"""A missing POSIX process group must not leave the timed-out child alive."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


@unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
class MissingProcessGroupTests(unittest.TestCase):
    def test_missing_group_still_terminates_direct_child(self):
        children = []
        real_popen = subprocess.Popen

        def track_spawn(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            children.append(process)
            return process

        try:
            with tempfile.TemporaryDirectory() as directory:
                with patch('devpilot.bounded_process.subprocess.Popen', side_effect=track_spawn):
                    with patch('devpilot.bounded_process.os.killpg', side_effect=ProcessLookupError):
                        result = run_bounded(
                            [sys.executable, '-c', 'import time; time.sleep(60)'],
                            Path(directory), timeout=0.05,
                        )
            self.assertEqual(result['error'], 'Timed out after 0.05s')
            self.assertIsNone(result['exit_code'])
            self.assertEqual(len(children), 1)
            self.assertIsNotNone(children[0].poll(), 'timed-out child is still alive')
            self.assertFalse(result['stdout_truncated'])
            self.assertFalse(result['stderr_truncated'])
        finally:
            for process in children:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
