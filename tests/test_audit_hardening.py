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

    def test_git_index_query_disables_fsmonitor_and_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('devpilot.audit.shutil.which', return_value='/usr/bin/git'):
                with patch('devpilot.audit.subprocess.run', return_value=subprocess.CompletedProcess([], 0, b'config/.env\0', b'')) as run:
                    report = audit_tracked_files(Path(directory))
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false'])
        self.assertEqual(argv[-3:], ['ls-files', '--cached', '-z'])
        self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
        self.assertEqual(report['candidates'], ['config/.env'])


if __name__ == '__main__':
    unittest.main()
