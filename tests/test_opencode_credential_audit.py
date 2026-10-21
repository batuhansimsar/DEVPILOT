"""Both Git index audits identify OpenCode credentials without opening files."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class OpenCodeCredentialAuditTests(unittest.TestCase):
    def test_both_audits_detect_auth_mcp_tokens_and_database(self):
        for path in (
            '.local/share/opencode/auth.json',
            '.local/share/opencode/mcp-auth.json',
            '.local/share/opencode/opencode.db',
            'data/opencode/opencode.db.bak',
            r'HOME\.LOCAL\SHARE\OPENCODE\MCP-AUTH.JSON',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential AI assistant OAuth credentials')

    def test_templates_and_unrelated_databases_are_not_flagged(self):
        for path in (
            'data/opencode.db',
            'data/mcp-auth.json',
            'project/opencode/opencode.db.example',
            'project/opencode/mcp-auth.json.sample',
            'project/opencode/sessions.db',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_tracked_files_only_and_redacted_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            tracked = (
                '.local/share/opencode/mcp-auth.json',
                '.local/share/opencode/opencode.db',
                '.local/share/opencode/opencode.db.example',
            )
            for path in (*tracked, 'untracked/opencode/mcp-auth.json'):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('NEVER_ECHO_SECRET_VALUE', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *tracked], check=True)
            first = audit_tracked_files(root)
            second = audit(root, redact_paths=True)
        self.assertEqual(first['tracked_files'], len(tracked))
        self.assertEqual(first['candidates'], list(tracked[:2]))
        self.assertEqual(len(second['findings']), 2)
        self.assertTrue(all('path' not in finding for finding in second['findings']))
        self.assertNotIn('NEVER_ECHO_SECRET_VALUE', repr(first) + repr(second))


if __name__ == '__main__':
    unittest.main()
