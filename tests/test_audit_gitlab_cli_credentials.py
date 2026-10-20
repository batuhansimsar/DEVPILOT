"""Regression coverage for GitLab CLI credential config detection."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class GitLabCLIConfigTests(unittest.TestCase):
    def test_sensitive_config_and_backup_names(self):
        for path in ('.config/glab-cli/config.yml', 'glab-cli/config.yml',
                     r'profile\.config\glab-cli\config.yml',
                     'Library/Application Support/glab-cli/config.yml',
                     'glab-cli/config.yml.bak.orig'):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_templates_and_other_configs_remain_safe(self):
        for path in ('docs/config.yml', 'gh/config.yml',
                     'glab-cli/config.yml.example',
                     '.config/glab-cli/config.yml.template.bak',
                     'glab-cli/README.md'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_git_index_audits_do_not_read_credential_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            paths = ('.config/glab-cli/config.yml', 'glab-cli/config.yml.backup', 'docs/config.yml')
            for name in paths:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('TOKEN_MUST_NOT_LEAK', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True, capture_output=True)
            report = audit_tracked_files(root)
            self.assertEqual(report['tracked_files'], 3)
            self.assertEqual(report['candidates'], sorted(paths[:2]))
            self.assertNotIn('TOKEN_MUST_NOT_LEAK', str(report))
            redacted = audit(root, redact_paths=True)
            self.assertEqual(redacted['tracked_files_checked'], 3)
            self.assertEqual(len(redacted['findings']), 2)
            self.assertTrue(all('path' not in item for item in redacted['findings']))
            self.assertNotIn('TOKEN_MUST_NOT_LEAK', str(redacted))


if __name__ == '__main__':
    unittest.main()
