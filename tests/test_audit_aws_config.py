"""Regression tests for AWS CLI config files in the compact Git index audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class AWSConfigAuditTests(unittest.TestCase):
    def test_config_can_hold_embedded_access_keys(self):
        for name in ('.aws/config', 'service/.aws/config',
                     'SERVICE\\.AWS\\CONFIG', '.aws/config.bak'):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_templates_and_unrelated_configs_not_flagged(self):
        for name in ('config', 'docs/config', '.aws/config.example',
                     '.aws/config.sample', '.aws/config.template'):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_git_index_only_reports_sensitive_aws_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('.aws/config', '.aws/config.example', 'docs/config', 'untracked.key'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('DO_NOT_DISCLOSE_AWS_SECRET', encoding='utf-8')
            subprocess.run(['git', 'add', '--', '.aws/config', '.aws/config.example',
                            'docs/config'], cwd=root, check=True)
            report = audit_tracked_files(root)
            self.assertNotIn('error', report)
            self.assertEqual(report['candidates'], ['.aws/config'])
            self.assertNotIn('DO_NOT_DISCLOSE_AWS_SECRET', repr(report))


if __name__ == '__main__':
    unittest.main()
