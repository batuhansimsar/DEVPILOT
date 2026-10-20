"""Cloud CLI token caches must be found by both filename-only Git audits."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import classify


class CloudTokenCacheTests(unittest.TestCase):
    def test_token_cache_filenames_are_sensitive(self):
        for name in (
            '.aws/cli/cache/1234abcd.json',
            'nested/.aws/sso/cache/token.json',
            r'HOME\\.AWS\\SSO\\CACHE\\TOKEN.JSON',
            '.aws/cli/cache/1234abcd.json.bak',
            '.config/gcloud/credentials.db',
            'home/.config/gcloud/access_tokens.db',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
                self.assertIsNotNone(classify(name))

    def test_unrelated_json_and_templates_are_ignored(self):
        for name in (
            'other/cache/token.json',
            '.aws/sso/other/token.json',
            '.aws/sso/cache/README.md',
            '.aws/cli/cache/token.json.example',
            '.config/gcloud/credentials.db.example',
            'docs/credentials.db',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))
                self.assertIsNone(classify(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_staged_token_cache_filenames_are_reported_without_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            tracked = (
                '.aws/cli/cache/abc.json',
                '.aws/sso/cache/def.json',
                '.config/gcloud/credentials.db',
                'docs/cache/session.json',
            )
            for name in (*tracked, '.aws/sso/cache/untracked.json'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('DUMMY_TOKEN_VALUE_DO_NOT_LOG', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *tracked], cwd=root, check=True, capture_output=True)
            result = audit_tracked_files(root)
            expected = sorted(tracked[:3])
            self.assertEqual(result['tracked_files'], len(tracked))
            self.assertEqual(result['candidates'], expected)
            self.assertNotIn('DUMMY_TOKEN_VALUE_DO_NOT_LOG', repr(result))
            self.assertNotIn('untracked.json', repr(result))


if __name__ == '__main__':
    unittest.main()
