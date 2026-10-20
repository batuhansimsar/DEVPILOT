"""Regression tests for filename-only Streamlit and Cloudflare secret audits."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class LocalSecretFilesTests(unittest.TestCase):
    def test_live_secret_files_detected_by_both_auditors(self):
        paths = (
            '.streamlit/secrets.toml',
            'app/.streamlit/secrets.toml',
            r'App\.STREAMLIT\SECRETS.TOML.bak',
            '.dev.vars',
            'worker/.dev.vars.production',
            'worker/.dev.vars.production.old',
            'worker/.dev.vars.production.example.local',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertIsNotNone(classify(path))

    def test_templates_and_unrelated_files_not_flagged(self):
        paths = (
            '.streamlit/secrets.toml.example',
            '.streamlit/secrets.toml.template.bak',
            'docs/secrets.toml',
            'src/.streamlit/config.toml',
            '.dev.vars.example',
            'worker/.dev.vars.staging.sample',
            '.dev.vars.dist.bak',
            'worker/wrangler.toml',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_live_secrets_are_reported_without_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            tracked = (
                '.streamlit/secrets.toml',
                'worker/.dev.vars.production',
                '.streamlit/secrets.toml.example',
                'worker/.dev.vars.production.sample',
                'docs/secrets.toml',
            )
            for name in (*tracked, 'untracked/.streamlit/secrets.toml'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('SECRET_VALUE_NEVER_OUTPUT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *tracked], cwd=root, check=True)
            simple = audit_tracked_files(root)
            detailed = audit(root)
            redacted = audit(root, redact_paths=True)

        expected = ['.streamlit/secrets.toml', 'worker/.dev.vars.production']
        self.assertNotIn('error', simple)
        self.assertEqual(simple['tracked_files'], len(tracked))
        self.assertEqual(simple['candidates'], expected)
        self.assertEqual(sorted(item['path'] for item in detailed['findings']), expected)
        self.assertEqual(len(redacted['findings']), 2)
        self.assertTrue(all('path' not in item for item in redacted['findings']))
        for report in (simple, detailed, redacted):
            self.assertNotIn('SECRET_VALUE_NEVER_OUTPUT', str(report))


if __name__ == '__main__':
    unittest.main()
