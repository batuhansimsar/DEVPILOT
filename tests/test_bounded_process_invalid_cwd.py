"""Malformed working directories cannot crash process-based diagnostics."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


class BoundedProcessWorkingDirectoryTests(unittest.TestCase):
    def test_nul_in_working_directory_is_reported_without_leaking_path(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / 'private\x00secret'
            result = run_bounded([sys.executable, '-c', 'pass'], root)
        self.assertIsNone(result['exit_code'])
        self.assertEqual(result['error'], 'Cannot start command: invalid working directory or process arguments')
        self.assertNotIn('secret', result['error'])

    def test_invalid_cwd_type_is_reported(self):
        result = run_bounded([sys.executable, '-c', 'pass'], object())
        self.assertIsNone(result['exit_code'])
        self.assertEqual(result['error'], 'Cannot start command: invalid working directory or process arguments')

    def test_popen_value_error_cannot_leak_private_paths(self):
        with patch('devpilot.bounded_process.subprocess.Popen', side_effect=ValueError('secret /tmp/private')):
            result = run_bounded([sys.executable, '-c', 'pass'], Path('.'))
        self.assertIsNone(result['exit_code'])
        self.assertEqual(result['error'], 'Cannot start command: invalid working directory or process arguments')
        self.assertNotIn('private', result['error'])

    def test_valid_cwd_still_executes_command(self):
        with TemporaryDirectory() as temp:
            result = run_bounded([sys.executable, '-c', 'print("ok")'], Path(temp))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ok\n')


if __name__ == '__main__':
    unittest.main()
