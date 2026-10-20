"""GitHub Copilot credential-store paths must be flagged without reading secrets."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class CopilotCredentialAuditTests(unittest.TestCase):
    def test_token_stores_are_detected_in_both_audits(self):
        for path in (
            '.config/github-copilot/apps.json',
            '.config/github-copilot/hosts.json',
            '.config/github-copilot/oauth.json',
            'home/.copilot/config.json',
            'HOME\\.CONFIG\\GITHUB-COPILOT\\APPS.JSON',
            '.config/github-copilot/hosts.json.bak',
            '.copilot/config.json.___jb_old___',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_unrelated_json_and_templates_are_not_flagged(self):
        for path in (
            'src/hosts.json',
            '.config/github-copilot/versions.json',
            'docs/github-copilot/apps.json',
            '.copilot/README.md',
            '.config/github-copilot/apps.json.example',
            '.copilot/config.json.sample',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_audits_only_staged_credentials_and_redacts_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            staged = (
                '.config/github-copilot/apps.json',
                '.config/github-copilot/hosts.json',
                '.copilot/config.json',
                '.config/github-copilot/versions.json',
            )
            for path in (*staged, 'untracked/.copilot/config.json'):
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('SENSITIVE_TOKEN_DO_NOT_EXPOSE', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *staged], check=True)

            first = audit_tracked_files(root)
            second = audit(root, redact_paths=True)

            self.assertEqual(first['tracked_files'], 4)
            self.assertEqual(set(first['candidates']), set(staged[:3]))
            self.assertEqual(second['tracked_files_checked'], 4)
            self.assertEqual(len(second['findings']), 3)
            self.assertTrue(all('path' not in item for item in second['findings']))
            self.assertNotIn('SENSITIVE_TOKEN_DO_NOT_EXPOSE', str(first))
            self.assertNotIn('SENSITIVE_TOKEN_DO_NOT_EXPOSE', str(second))


if __name__ == '__main__':
    unittest.main()
