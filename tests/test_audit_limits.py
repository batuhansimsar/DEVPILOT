"""Limit regression tests for the read-only Git filename audit."""

import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import audit_tracked_files


class AuditLimitsTests(unittest.TestCase):
    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.audit._tracked_paths')
    def test_rejects_oversized_index_before_processing_paths(self, run, which):
        run.return_value = b'x' * (8 * 1024 * 1024 + 1)
        report = audit_tracked_files(Path('.'))
        self.assertIn('8 MiB', report['error'])
        self.assertEqual(report['tracked_files'], 0)
        self.assertEqual(report['candidates'], [])

    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.audit._tracked_paths')
    def test_rejects_more_than_100000_tracked_paths(self, run, which):
        run.return_value = b'x\0' * 100_001
        report = audit_tracked_files(Path('.'))
        self.assertIn('100,000', report['error'])
        self.assertEqual(report['tracked_files'], 0)
        self.assertEqual(report['candidates'], [])

    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    @patch('devpilot.audit._tracked_paths')
    def test_100000_path_boundary_is_accepted(self, run, which):
        run.return_value = b'x\0' * 100_000
        report = audit_tracked_files(Path('.'))
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 100_000)
        self.assertEqual(report['candidates'], [])


if __name__ == '__main__':
    unittest.main()
