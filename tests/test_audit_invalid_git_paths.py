"""Regression tests for byte-distinct Git filenames in the audit report."""

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import audit_tracked_files


class AuditInvalidGitPathsTests(unittest.TestCase):
    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    def test_undecodable_sensitive_paths_remain_distinct(self, _which):
        completed = subprocess.CompletedProcess([], 0, stdout=b'.env.\xff\0.env.\xfe\0')
        with patch('devpilot.audit._tracked_paths', return_value=completed.stdout):
            report = audit_tracked_files(Path('/tmp/public'))
        self.assertEqual(report['tracked_files'], 2)
        self.assertEqual(len(report['candidates']), 2)
        self.assertEqual(
            {path.encode('utf-8', errors='surrogateescape') for path in report['candidates']},
            {b'.env.\xff', b'.env.\xfe'},
        )
        # JSON CLI uses the default ASCII-safe encoding for surrogate escapes.
        json.dumps(report).encode('utf-8')

    @patch('devpilot.audit.shutil.which', return_value='/usr/bin/git')
    def test_regular_unicode_paths_are_unchanged(self, _which):
        completed = subprocess.CompletedProcess([], 0, stdout='şifre/.env'.encode() + b'\0')
        with patch('devpilot.audit._tracked_paths', return_value=completed.stdout):
            report = audit_tracked_files(Path('/tmp/public'))
        self.assertEqual(report['candidates'], ['şifre/.env'])


if __name__ == '__main__':
    unittest.main()
