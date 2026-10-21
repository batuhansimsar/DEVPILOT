"""Claude Code local settings can contain secrets despite a generic JSON name."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.agent_credentials import is_agent_local_settings


class LocalSettingsDetectionTests(unittest.TestCase):
    def test_recognizes_scoped_sensitive_local_settings(self):
        for parts in (
            ('.claude', 'settings.local.json'),
            ('nested', 'project', '.claude', 'settings.local.json'),
        ):
            with self.subTest(parts=parts):
                self.assertTrue(is_agent_local_settings(parts))

    def test_does_not_flag_templates_or_other_settings(self):
        for parts in (
            (), ('settings.local.json',),
            ('docs', 'settings.local.json'),
            ('.claude', 'settings.json'),
            ('.gemini', 'settings.local.json'),
            ('.claude', 'settings.local.json.example'),
            ('claude', 'settings.local.json'),
        ):
            with self.subTest(parts=parts):
                self.assertFalse(is_agent_local_settings(parts))

    def test_both_audits_flag_local_settings_and_backups(self):
        from devpilot.audit import _potential_secret
        from devpilot.secret_audit import classify

        for path in (
            '.claude/settings.local.json',
            'app/.claude/settings.local.json',
            r'PROJECT\.CLAUDE\SETTINGS.LOCAL.JSON',
            '.claude/settings.local.json.bak',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path),
                                 'potential AI assistant local settings with embedded credentials')

        for path in (
            'docs/settings.local.json',
            '.claude/settings.json',
            '.claude/settings.local.json.example',
            '.claude/settings.local.json.sample.bak',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_git_index_audits_detect_without_reading_contents(self):
        from devpilot.audit import audit_tracked_files
        from devpilot.secret_audit import audit

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True,
                           capture_output=True)
            paths = (
                '.claude/settings.local.json',
                '.claude/settings.local.json.bak',
                '.claude/settings.local.json.example',
            )
            for name in paths:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('SECRET_VALUE_DO_NOT_PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True,
                           capture_output=True)
            basic = audit_tracked_files(root)
            private = audit(root, redact_paths=True)

        self.assertEqual(basic['tracked_files'], len(paths))
        self.assertEqual(basic['candidates'], list(paths[:2]))
        self.assertEqual(len(private['findings']), 2)
        self.assertTrue(all('path' not in item for item in private['findings']))
        self.assertNotIn('SECRET_VALUE_DO_NOT_PRINT', repr(basic) + repr(private))


if __name__ == '__main__':
    unittest.main()
