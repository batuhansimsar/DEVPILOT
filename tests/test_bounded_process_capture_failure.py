"""Capture errors must be reported, never mistaken for successful diagnostics."""

import errno
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.bounded_process import _capture_tail, run_bounded


class CaptureFailureTests(unittest.TestCase):
    def test_reader_failure_flag_does_not_expose_private_os_error(self):
        read_fd, write_fd = os.pipe()
        os.close(write_fd)
        tail, total, failed = bytearray(), [0], [False]
        with os.fdopen(read_fd, 'rb') as reader:
            with patch('devpilot.bounded_process.os.read', side_effect=OSError(errno.EIO, '/private/secret.txt')):
                _capture_tail(reader, tail, total, failed)
        self.assertTrue(failed[0])
        self.assertEqual(tail, b'')
        self.assertEqual(total, [0])

    def test_successful_child_with_failed_capture_is_not_reported_as_success(self):
        def failed_capture(stream, tail, totals, read_failed):
            read_failed[0] = True
            stream.close()

        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.bounded_process._capture_tail', side_effect=failed_capture):
                result = run_bounded([sys.executable, '-c', 'pass'], Path(directory))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['error'], 'Cannot capture command output')
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])
        self.assertNotIn('/private', str(result))

    def test_normal_output_has_no_capture_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_bounded([sys.executable, '-c', "print('ok')"], Path(directory))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ok\n')
        self.assertNotIn('error', result)
        self.assertFalse(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])


if __name__ == '__main__':
    unittest.main()
