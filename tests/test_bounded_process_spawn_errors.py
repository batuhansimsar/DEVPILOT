"""Spawn errors must not expose private paths or terminal escape sequences."""

import errno
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


class SpawnErrorRedactionTests(unittest.TestCase):
    def test_spawn_errors_report_only_errno(self):
        failures = (
            (FileNotFoundError(errno.ENOENT, 'secret\x1b[31m', '/private/credential'), 'ENOENT'),
            (PermissionError(errno.EACCES, 'api-key\nvalue', '/private/credential'), 'EACCES'),
            (OSError('private diagnostic\x1b[2J'), 'I/O error'),
        )
        with tempfile.TemporaryDirectory() as folder:
            for exception, reason in failures:
                with self.subTest(reason=reason):
                    with patch('devpilot.bounded_process.subprocess.Popen', side_effect=exception):
                        result = run_bounded(['test-command'], Path(folder))
                    self.assertEqual(result['error'], f'Cannot start command: {reason}')
                    self.assertIsNone(result['exit_code'])
                    self.assertNotIn('private', result['error'])
                    self.assertNotIn('\x1b', result['error'])
                    self.assertNotIn('\n', result['error'])

    def test_missing_executable_reports_stable_code(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_bounded(['devpilot-missing-executable-123456'], Path(folder))
        self.assertEqual(result['error'], 'Cannot start command: ENOENT')
        self.assertIsNone(result['exit_code'])

    def test_successful_command_is_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_bounded([sys.executable, '-c', 'print("ok")'], Path(folder))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ok\n')
        self.assertNotIn('error', result)


if __name__ == '__main__':
    unittest.main()
