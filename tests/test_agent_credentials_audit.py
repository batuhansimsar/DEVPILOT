"""Both audits must recognize AI coding assistant OAuth token stores."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class AgentCredentialsAuditTests(unittest.TestCase):
    def test_assistant_token_locations_and_backup_copies(self):
        for path in (
            '.claude/.credentials.json',
            'nested/.gemini/oauth_creds.json',
            r'HOME\.CLAUDE\.CREDENTIALS.JSON',
            '.gemini/oauth_creds.json.bak',
            '.claude/.credentials.json.~2~',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential AI assistant OAuth credentials')

    def test_templates_and_generic_files_are_not_flagged(self):
        for path in (
            'docs/.credentials.json',
            'docs/oauth_creds.json',
            '.claude/settings.json',
            '.gemini/settings.json',
            '.gemini/oauth_creds.json.example',
            '.claude/.credentials.json.sample.bak',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_tracked_agent_credentials_detected_without_reading_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            tracked = (
                '.claude/.credentials.json',
                '.gemini/oauth_creds.json',
                '.gemini/oauth_creds.json.example',
            )
            for name in (*tracked, 'untracked/.claude/.credentials.json'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PRIVATE_OAUTH_TOKEN_NEVER_LOG', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *tracked], check=True)
            basic = audit_tracked_files(root)
            private = audit(root, redact_paths=True)
        self.assertEqual(basic['candidates'], list(tracked[:2]))
        self.assertEqual(len(private['findings']), 2)
        self.assertTrue(all('path' not in finding for finding in private['findings']))
        self.assertNotIn('PRIVATE_OAUTH_TOKEN_NEVER_LOG', repr(basic) + repr(private))


if __name__ == '__main__':
    unittest.main()
