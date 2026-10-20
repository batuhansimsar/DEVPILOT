"""GitLab Runner configuration can expose registration/authentication tokens."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class GitLabRunnerCredentialsTests(unittest.TestCase):
    def test_runner_config_locations_and_backup_copies(self):
        paths = (
            '.gitlab-runner/config.toml',
            'etc/gitlab-runner/config.toml',
            r'HOME\\.GITLAB-RUNNER\\CONFIG.TOML',
            'build/gitlab-runner/config.toml.bak.old',
            '.gitlab-runner/config.toml.swp',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_unrelated_configs_and_templates_are_not_flagged(self):
        paths = (
            'config.toml',
            'docs/config.toml',
            'gitlab-runner/config.toml.example',
            '.gitlab-runner/config.toml.example.bak',
            'gitlab-runner/config.sample.toml',
            'gitlab-runner/README.md',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_tracked_only_and_redacted_findings_never_read_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            tracked = (
                'ci/gitlab-runner/config.toml',
                '.gitlab-runner/config.toml.bak',
                'docs/config.toml',
                'gitlab-runner/config.toml.example',
            )
            for relative in (*tracked, 'untracked/gitlab-runner/config.toml'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('SECRET_FIXTURE_DO_NOT_PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *tracked],
                           cwd=root, check=True, capture_output=True)
            basic = audit_tracked_files(root)
            redacted = audit(root, redact_paths=True)

        self.assertEqual(basic['tracked_files'], len(tracked))
        self.assertEqual(basic['candidates'], sorted(tracked[:2]))
        self.assertNotIn('SECRET_FIXTURE_DO_NOT_PRINT', repr(basic))
        self.assertEqual(redacted['tracked_files_checked'], len(tracked))
        self.assertEqual(len(redacted['findings']), 2)
        self.assertTrue(all('path' not in item for item in redacted['findings']))
        self.assertNotIn('SECRET_FIXTURE_DO_NOT_PRINT', repr(redacted))


if __name__ == '__main__':
    unittest.main()
