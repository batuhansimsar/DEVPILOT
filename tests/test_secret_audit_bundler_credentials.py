"""Both Git index audits recognize Ruby Bundler token-bearing config files."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class BundlerAuditTests(unittest.TestCase):
    def test_bundler_configs_and_editor_backups_are_flagged(self):
        for path in (
            '.bundle/config',
            'project/.bundle/config',
            r'C:\Users\developer\.bundle\config',
            '.bundle/config.bak',
            'home/.bundle/config.swp',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential Bundler registry credentials')

    def test_generic_configs_and_samples_are_not_flagged(self):
        for path in (
            'config', 'docs/config', 'bundle/config',
            '.bundle/config.example', 'project/.bundle/config.sample',
            '.bundle/config.template.bak', '.bundle/README.md',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_staged_bundler_config_flagged_without_opening_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            paths = ('.bundle/config', 'project/.bundle/config',
                     '.bundle/config.example', 'docs/config')
            for relative in paths:
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('PRIVATE_BUNDLER_TOKEN_NEVER_OUTPUT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '-f', '--', *paths], check=True)
            with patch('pathlib.Path.read_text', side_effect=AssertionError('must not read credentials')):
                detailed = audit(root, redact_paths=True)
                concise = audit_tracked_files(root)
            self.assertEqual(detailed['tracked_files_checked'], len(paths))
            self.assertEqual(len(detailed['findings']), 2)
            self.assertTrue(all('path' not in item for item in detailed['findings']))
            self.assertEqual(concise['candidates'], ['.bundle/config', 'project/.bundle/config'])
            self.assertNotIn('PRIVATE_BUNDLER_TOKEN_NEVER_OUTPUT', json.dumps(detailed))
            self.assertNotIn('PRIVATE_BUNDLER_TOKEN_NEVER_OUTPUT', json.dumps(concise))


if __name__ == '__main__':
    unittest.main()
