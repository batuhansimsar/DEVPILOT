"""Safe Git index audit tests with no credentials or network usage."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from devpilot.audit import _potential_secret, audit_tracked_files


class AuditTests(unittest.TestCase):
    def test_sensitive_names(self):
        for path in ('config/.env', '.env.production', 'private/id_ed25519', 'tls/server.key', 'credentials.json', '.npmrc'):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_examples_and_normal_files(self):
        for path in ('config/.env.example', '.env.template', 'src/main.py', 'package-lock.json', 'README.md'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    def test_git_missing_returns_explanation(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp, patch('devpilot.audit.shutil.which', return_value=None):
            self.assertIn('error', audit_tracked_files(Path(temp)))

    @unittest.skipUnless(shutil.which('git'), 'Git not installed')
    def test_only_tracked_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            (root / '.env').write_text('DUMMY=placeholder\n')
            (root / '.env.example').write_text('DUMMY=example\n')
            (root / 'credentials.json').write_text('{}')
            (root / 'id_ed25519').write_text('untracked placeholder')
            subprocess.run(['git', '-C', str(root), 'add', '.env', '.env.example', 'credentials.json'], check=True, capture_output=True)
            result = audit_tracked_files(root)
            self.assertEqual(result['tracked_files'], 3)
            self.assertEqual(result['candidates'], ['.env', 'credentials.json'])
            self.assertNotIn('error', result)

    @unittest.skipUnless(shutil.which('git'), 'Git not installed')
    def test_non_repo_is_friendly_error(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertIn('error', audit_tracked_files(Path(temp)))


if __name__ == '__main__':
    unittest.main()
