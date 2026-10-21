"""Vercel and Netlify CLI token stores are reported without reading secrets."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.cloud_cli_credentials import is_cloud_cli_credential_location
from devpilot.secret_audit import audit, classify


class VercelNetlifyCredentialAuditTests(unittest.TestCase):
    def test_os_specific_auth_files_in_both_audits(self):
        sensitive = (
            '.local/share/com.vercel.cli/auth.json',
            'Library/Application Support/com.vercel.cli/auth.json',
            '.config/netlify/config.json',
            'Library/Preferences/netlify/config.json',
            r'AppData\Roaming\netlify\Config\config.json',
        )
        for path in sensitive:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential cloud CLI credential configuration')
                normalized = tuple(part.lower() for part in path.replace('\\', '/').split('/'))
                self.assertTrue(is_cloud_cli_credential_location(normalized))

    def test_unrelated_configurations_and_templates_are_safe(self):
        safe = (
            'docs/netlify/config.json',
            '.config/netlify/config.json.example',
            'Library/Preferences/netlify/config.json.sample',
            'docs/com.vercel.cli/config.json',
            'docs/vercel/settings.json',
            'src/stripe/config.toml',
        )
        for path in safe:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_audits_ignore_untracked_files_and_redact_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            sensitive = ('.config/netlify/config.json', '.local/share/com.vercel.cli/auth.json')
            safe = ('docs/netlify/config.json',)
            for path in (*sensitive, *safe, 'untracked/netlify/config.json'):
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('PRIVATE_TOKEN_MUST_NOT_APPEAR', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *sensitive, *safe],
                           cwd=root, check=True, capture_output=True)
            summary = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)
        self.assertEqual(summary['tracked_files'], 3)
        self.assertEqual(summary['candidates'], sorted(sensitive))
        self.assertEqual(len(detailed['findings']), 2)
        self.assertTrue(all(item['category'] == 'potential cloud CLI credential configuration'
                            and 'path' not in item for item in detailed['findings']))
        self.assertNotIn('PRIVATE_TOKEN_MUST_NOT_APPEAR', repr(summary) + repr(detailed))
        self.assertNotIn('untracked', repr(summary))


if __name__ == '__main__':
    unittest.main()
