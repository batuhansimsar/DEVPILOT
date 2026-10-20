"""Preserve distinct non-UTF-8 Git filenames and avoid invalid Unicode in reports."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.secret_audit import audit


class InvalidUTF8AuditTests(unittest.TestCase):
    def test_invalid_utf8_paths_remain_distinct_and_json_safe(self):
        paths = b'private/secret.\xfe.pem\0private/secret.\xff.pem\0'
        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.secret_audit._tracked_paths', return_value=paths):
                report = audit(Path(directory))
        self.assertEqual(report['tracked_files_checked'], 2)
        self.assertEqual([finding['path'] for finding in report['findings']],
                         [r'private/secret.\udcfe.pem', r'private/secret.\udcff.pem'])
        self.assertNotIn('\ufffd', str(report))
        json.dumps(report, ensure_ascii=False).encode('utf-8')

    def test_valid_unicode_and_control_paths_are_unchanged(self):
        path = 'şifre/\x1b[31m.key'
        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.secret_audit._tracked_paths',
                       return_value=path.encode('utf-8') + b'\0'):
                report = audit(Path(directory))
        self.assertEqual(report['findings'][0]['path'], path)

    def test_redacted_report_exposes_no_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.secret_audit._tracked_paths',
                       return_value=b'secret.\xff.pem\0'):
                report = audit(Path(directory), redact_paths=True)
        self.assertNotIn('path', report['findings'][0])
        self.assertEqual(len(report['findings']), 1)


if __name__ == '__main__':
    unittest.main()
