"""Regression checks for read-only Git auditing and env template exclusions."""

import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import _potential_secret, audit_tracked_files


class AuditHardeningTests(unittest.TestCase):
    def test_environment_template_suffixes_not_sensitive(self):
        for name in ('.env.production.example', 'service/.env.local.sample',
                     '.env.prod.template', '.env.dev.dist', '.env.qa.defaults'):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    def test_non_template_environment_file_detected(self):
        for name in ('.env', '.env.local', 'service/.env.production'):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_tracked_templates_are_not_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            (root / '.env.production.example').write_text('SAMPLE=not-secret\n')
            (root / '.env.production').write_text('DUMMY=placeholder\n')
            subprocess.run(['git', '-C', str(root), 'add', '.env.production.example', '.env.production'],
                           check=True, capture_output=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 2)
        self.assertEqual(report['candidates'], ['.env.production'])

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_query_disables_fsmonitor_and_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            (root / '.env').write_text('DUMMY=not-logged', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.env'], check=True)
            with patch('devpilot.secret_audit.subprocess.Popen', wraps=subprocess.Popen) as spawn:
                report = audit_tracked_files(root)
        argv = spawn.call_args.args[0]
        self.assertEqual(argv[:4], ['git', '-c', 'core.fsmonitor=false', '--no-optional-locks'])
        self.assertEqual(argv[-3:], ['ls-files', '-z', '--cached'])
        self.assertEqual(spawn.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(report['candidates'], ['.env'])

if __name__ == '__main__':
    unittest.main()
