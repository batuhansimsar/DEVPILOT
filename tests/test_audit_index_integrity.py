"""Ensure malformed Git index streams cannot falsely clear a credential audit."""

import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import audit_tracked_files


class AuditIndexIntegrityTests(unittest.TestCase):
    def _audit_output(self, payload: bytes):
        with patch('devpilot.audit.shutil.which', return_value='/usr/bin/git'), \
             patch('devpilot.audit._tracked_paths', return_value=payload):
            return audit_tracked_files(Path('/sample'))

    def test_complete_records_are_audited(self):
        result = self._audit_output(b'.env\0docs/README.md\0')
        self.assertNotIn('error', result)
        self.assertEqual(result['tracked_files'], 2)
        self.assertEqual(result['candidates'], ['.env'])

    def test_incomplete_last_record_does_not_return_false_clean_report(self):
        for payload in (b'.env', b'docs/README.md\0secrets.json', b'git-index-partial'):
            with self.subTest(payload=payload):
                result = self._audit_output(payload)
                self.assertIn('Malformed Git index output', result['error'])
                self.assertEqual(result['tracked_files'], 0)

    def test_empty_records_are_rejected(self):
        for payload in (b'\0', b'.env\0\0', b'\0src/main.py\0'):
            with self.subTest(payload=payload):
                result = self._audit_output(payload)
                self.assertIn('Malformed Git index output', result['error'])
                self.assertEqual(result['tracked_files'], 0)

    def test_empty_repository_remains_valid(self):
        result = self._audit_output(b'')
        self.assertNotIn('error', result)
        self.assertEqual(result['tracked_files'], 0)

    def test_git_spawn_errors_do_not_expose_sensitive_exception_text(self):
        with patch('devpilot.audit.shutil.which', return_value='/usr/bin/git'), \
             patch('devpilot.secret_audit.subprocess.Popen',
                   side_effect=OSError('private-token-should-not-leak')):
            result = audit_tracked_files(Path('/sample'))
        self.assertIn('Unable to inspect Git index', result['error'])
        self.assertNotIn('private-token-should-not-leak', str(result))


if __name__ == '__main__':
    unittest.main()
