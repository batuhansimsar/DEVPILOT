"""Protect Git filename auditing from leaking subprocess exception details."""

import errno
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import audit_tracked_files


class AuditExceptionPrivacyTests(unittest.TestCase):
    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.secret_audit.subprocess.Popen')
    def test_os_error_omits_filename_and_private_message(self, run, _which):
        run.side_effect = FileNotFoundError(
            errno.ENOENT, 'private credential in strerror', '/home/user/.aws/credentials'
        )
        report = audit_tracked_files(Path('.'))
        self.assertEqual(report['error'], 'Unable to inspect Git index')
        self.assertEqual(report['candidates'], [])
        self.assertNotIn('credential', str(report))
        self.assertNotIn('.aws', str(report))

    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.secret_audit.subprocess.Popen')
    def test_timeout_omits_arguments_and_captured_output(self, run, _which):
        run.return_value.stdout = io.BytesIO(b'')
        run.return_value.wait.side_effect = [subprocess.TimeoutExpired(
            cmd=['git', 'sensitive-token'], timeout=10,
            output=b'private-material', stderr=b'secret'
        ), 0]
        report = audit_tracked_files(Path('.'))
        self.assertEqual(report['error'], 'Git index inspection timed out')
        self.assertNotIn('sensitive-token', str(report))
        self.assertNotIn('private-material', str(report))

    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.secret_audit.subprocess.Popen')
    def test_os_error_without_errno_omits_private_message(self, run, _which):
        run.side_effect = OSError('private operating system message')
        report = audit_tracked_files(Path('.'))
        self.assertEqual(report['error'], 'Unable to inspect Git index')
        self.assertNotIn('private', str(report))


if __name__ == '__main__':
    unittest.main()
