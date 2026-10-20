"""Preserve valid empty positional arguments without relaxing executable safety."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


class EmptyArgumentsTests(unittest.TestCase):
    def test_empty_positional_argument_is_forwarded(self):
        with TemporaryDirectory() as folder:
            result = run_bounded(
                [sys.executable, '-c',
                 'import sys; print(repr(sys.argv[1]))', ''],
                Path(folder), timeout=5,
            )
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], "''\n")
        self.assertNotIn('error', result)

    def test_empty_executable_is_rejected_without_spawn(self):
        with TemporaryDirectory() as folder, patch('devpilot.bounded_process.subprocess.Popen') as popen:
            result = run_bounded(['', 'valid-argument'], Path(folder))
        self.assertIsNone(result['exit_code'])
        self.assertIn('argv', result['error'])
        popen.assert_not_called()

    def test_embedded_nul_still_rejected_without_spawn(self):
        with TemporaryDirectory() as folder, patch('devpilot.bounded_process.subprocess.Popen') as popen:
            result = run_bounded(['echo', 'a\0b'], Path(folder))
        self.assertIsNone(result['exit_code'])
        self.assertIn('argv', result['error'])
        popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
