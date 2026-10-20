"""Regression tests for the independent tracked-secret safety audit."""

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify, main


class ClassificationTests(unittest.TestCase):
    def test_sensitive_filenames(self):
        for name in ('.env', '.env.production', 'config/.env.local', 'id_rsa', 'nested/private.key', 'service-account.json', 'credentials.json', '.npmrc', 'backup.p12'):
            with self.subTest(name=name):
                self.assertIsNotNone(classify(name))

    def test_examples_and_public_files_not_flagged(self):
        for name in ('.env.example', '.env.sample', 'README.md', 'id_rsa.pub', 'cert.crt', 'credentials.example.json', 'src/main.py'):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))

    def test_windows_style_paths(self):
        self.assertIsNotNone(classify('nested\\secret.pem'))

    def test_backed_up_secrets_are_flagged(self):
        for name in ('id_rsa.bak', 'nested/id_ed25519.old.bak', '.npmrc~', 'service-account.json.backup', 'private.key.orig', '.env.example.production'):
            with self.subTest(name=name):
                self.assertIsNotNone(classify(name))

    def test_template_backups_and_nonsecret_backups_are_ignored(self):
        for name in ('.env.example.bak', '.env.defaults.old', 'id_rsa.pub.bak', 'README.md.backup', 'credentials.sample.json.orig'):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))


@unittest.skipUnless(shutil.which('git'), 'Git is not installed')
class RepoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, stdout=subprocess.DEVNULL)

    def add(self, name, contents='anything'):
        destination = self.root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contents, encoding='utf-8')
        subprocess.run(['git', 'add', '--', name], cwd=self.root, check=True, stdout=subprocess.DEVNULL)

    def test_audit_only_tracks_staged_sensitive_paths(self):
        self.add('src/main.py')
        self.add('config/.env', 'PRIVATE_VALUE=do_not_print')
        (self.root / 'untracked.key').write_text('not tracked')
        result = audit(self.root)
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['path'], 'config/.env')
        self.assertNotIn('do_not_print', json.dumps(result))
        self.assertNotIn('untracked.key', json.dumps(result))

    def test_redaction_keeps_category(self):
        self.add('private.pem', 'very_secret')
        result = audit(self.root, redact_paths=True)
        self.assertEqual(len(result['findings']), 1)
        self.assertNotIn('path', result['findings'][0])
        self.assertIn('private key', result['findings'][0]['category'])

    def test_cli_json_and_exit_codes(self):
        self.add('.env', 'token=secret')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.root), '--json', '--redact-paths'])
        self.assertEqual(code, 1)
        self.assertEqual(len(json.loads(output.getvalue())['findings']), 1)
        self.assertNotIn('.env', output.getvalue())

    def test_clean_repo(self):
        self.add('main.py')
        self.assertTrue(audit(self.root)['ok'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.root)]), 0)

    def test_missing_directory(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.root / 'missing')]), 2)

    def test_audit_finds_backed_up_credentials(self):
        self.add('keys/id_rsa.old', 'do_not_print')
        self.add('.env.example.production', 'also_do_not_print')
        self.add('.env.example.bak', 'template')
        result = audit(self.root, redact_paths=True)
        self.assertEqual(result['tracked_files_checked'], 3)
        self.assertEqual(len(result['findings']), 2)
        self.assertNotIn('do_not_print', json.dumps(result))
        self.assertNotIn('also_do_not_print', json.dumps(result))
        self.assertTrue(all('path' not in finding for finding in result['findings']))


if __name__ == '__main__':
    unittest.main()
