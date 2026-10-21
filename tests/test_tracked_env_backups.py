"""Only live dotenv and their backups should be reported in the Git index scan."""

import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.security import _is_sensitive_env_filename, tracked_environment_files


class TrackedEnvBackupsTests(unittest.TestCase):
    def test_template_backup_files_remain_safe(self):
        for name in ('.env.example.bak', '.env.production.template.old',
                     'production.env.sample.orig', '.env.dist.~2~',
                     '..env.example.swp', '#.env.sample#', '.env.defaults.___jb_old___'):
            with self.subTest(name=name):
                self.assertFalse(_is_sensitive_env_filename(name))

    def test_sensitive_env_and_backups_are_flagged(self):
        for name in ('.env.bak', '.env.production.old', 'production.env.orig',
                     'production.env.example.local.bak', '..env.swp',
                     '..env.production.swp', '.env.local.~2~',
                     '.env.production.___jb_tmp___'):
            with self.subTest(name=name):
                self.assertTrue(_is_sensitive_env_filename(name))

    def test_git_index_report_filters_templates_but_preserves_paths(self):
        paths = [
            '.env.example.bak', 'apps/production.env.sample.orig',
            'api/.env.production.old', 'api/.env.example.local.bak',
            '..env.swp', 'api/.env.production.template.old',
        ]
        with patch('devpilot.security.shutil.which', return_value='git'), patch(
            'devpilot.security._tracked_paths', return_value=('\0'.join(paths) + '\0').encode()
        ) as scan:
            findings = tracked_environment_files(Path('/tmp/project'))
        self.assertEqual(findings, sorted(['api/.env.production.old',
                                           'api/.env.example.local.bak', '..env.swp']))
        scan.assert_called_once_with(Path('/tmp/project'))

    def test_malformed_index_still_returns_no_findings(self):
        with patch('devpilot.security.shutil.which', return_value='git'), patch(
            'devpilot.security._tracked_paths', return_value=b'.env.bak'
        ):
            self.assertEqual(tracked_environment_files(Path('.')), [])


if __name__ == '__main__':
    unittest.main()
