"""GitLab CLI authentication config must be included in read-only filename audits."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class GitLabCLIAuditTests(unittest.TestCase):
    def test_detects_gitlab_cli_config_and_backup_paths(self):
        cases = (
            '.config/glab-cli/config.yml',
            '.config/glab-cli/config.yaml',
            'home/.config/glab-cli/config.yml',
            r'Users\user\.config\glab-cli\config.yml',
            '.config/glab-cli/config.yml.bak',
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_other_configs_and_templates_remain_unflagged(self):
        cases = (
            'docs/config.yml',
            '.config/git/config.yml',
            '.config/glab-cli/README.md',
            '.config/glab-cli/config.yml.example',
            '.config/glab-cli/config.yaml.sample',
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_tracked_config_is_reported_without_reading_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            config = root / '.config/glab-cli/config.yml'
            config.parent.mkdir(parents=True)
            config.write_text('token: never-print-this-gitlab-token\n', encoding='utf-8')
            (root / 'README.md').write_text('safe\n', encoding='utf-8')
            subprocess.run(['git', 'add', '--', '.config/glab-cli/config.yml', 'README.md'],
                           cwd=root, check=True)
            report = audit(root, redact_paths=True)
        self.assertFalse(report['ok'])
        self.assertEqual(report['tracked_files_checked'], 2)
        self.assertEqual(len(report['findings']), 1)
        self.assertEqual(report['findings'][0]['category'], 'potential credential configuration')
        self.assertNotIn('path', report['findings'][0])
        self.assertNotIn('never-print-this-gitlab-token', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
