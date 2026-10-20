"""Ensure a partial Git index stream cannot falsely clear a credential audit."""

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from devpilot.audit import audit_tracked_files


class AuditIndexIntegrityTests(unittest.TestCase):
    def _audit_output(self, payload: bytes):
        with patch('devpilot.audit.shutil.which', return_value='/usr/bin/git'), \
             patch('devpilot.audit.subprocess.run', return_value=SimpleNamespace(
                 stdout=payload, returncode=0)):
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
                self.assertIn('Incomplete Git index output', result['error'])
                self.assertEqual(result['tracked_files'], 0)

    def test_empty_repository_remains_valid(self):
        result = self._audit_output(b'')
        self.assertNotIn('error', result)
        self.assertEqual(result['tracked_files'], 0)

    def test_git_errors_do_not_echo_sensitive_exceptions(self):
        failures = (
            OSError('private-token-should-not-leak'),
            subprocess.TimeoutExpired(['git', 'private-token-should-not-leak'], 10),
        )
        for failure in failures:
            with self.subTest(type=type(failure).__name__), \
                 patch('devpilot.audit.shutil.which', return_value='/usr/bin/git'), \
                 patch('devpilot.audit.subprocess.run', side_effect=failure):
                result = audit_tracked_files(Path('/sample'))
                self.assertIn('error', result)
                self.assertNotIn('private-token-should-not-leak', str(result))


if __name__ == '__main__':
    unittest.main()
