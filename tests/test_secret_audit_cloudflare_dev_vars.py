"""Keep both tracked-secret scanners consistent for Cloudflare Workers files."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class CloudflareDevVarsAuditTests(unittest.TestCase):
    def test_sensitive_worker_secrets_and_backups(self):
        for path in (
            '.dev.vars',
            'worker/.dev.vars.production',
            r'worker\.dev.vars.staging',
            'worker/.dev.vars.example.local',
            '.dev.vars.bak',
            'worker/.dev.vars.production.old',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential Cloudflare Workers environment file')
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_paths_remain_clean(self):
        for path in (
            '.dev.vars.example',
            '.dev.vars.sample',
            'worker/.dev.vars.staging.template',
            '.dev.vars.dist.bak',
            'worker/.dev.vars.defaults',
            'worker/wrangler.toml',
            'worker/dev.vars',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_both_git_index_scanners_flag_secrets_without_reading_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            paths = (
                '.dev.vars',
                'worker/.dev.vars.production',
                'worker/.dev.vars.example',
                'README.md',
            )
            for relative in paths:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text('CLOUDFLARE_TOKEN=do-not-echo-me\n', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True, capture_output=True)

            detailed = audit(root, redact_paths=True)
            concise = audit_tracked_files(root)
            self.assertEqual(detailed['tracked_files_checked'], 4)
            self.assertEqual(len(detailed['findings']), 2)
            self.assertTrue(all('path' not in item for item in detailed['findings']))
            self.assertEqual(concise['candidates'], ['.dev.vars', 'worker/.dev.vars.production'])
            self.assertNotIn('do-not-echo-me', str(detailed))
            self.assertNotIn('do-not-echo-me', str(concise))


if __name__ == '__main__':
    unittest.main()
