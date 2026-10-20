"""Regression tests for the independent tracked-secret safety audit."""

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_additional_sensitive_filenames_and_contexts(self):
        for name in (
            'infra/terraform.tfstate', 'infra/prod.tfstate.backup',
            'project/.aws/credentials', '.kube/config', 'home/.docker/config.json',
            'deploy/secrets.yaml', 'deploy/secrets.yml', '.envrc',
            'certs/identity.jks', 'certs/signing.keystore',
            'PROJECT\\.AWS\\CREDENTIALS',
        ):
            with self.subTest(name=name):
                self.assertIsNotNone(classify(name))

    def test_context_sensitive_config_detection_avoids_generic_false_positives(self):
        for name in ('config', 'src/config.json', 'docs/credentials.example.json',
                     'terraform.tfstate.example', 'docs/example.tfstate.sample',
                     'foo/.aws/readme', 'foo/.docker/config.example.json'):
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

    def test_extended_findings_in_git_index_without_reading_secret_contents(self):
        self.add('.aws/credentials', 'aws_secret_access_key=super-secret')
        self.add('infrastructure/prod.tfstate', 'sensitive-value')
        self.add('docs/config.json', 'safe')
        result = audit(self.root, redact_paths=True)
        self.assertEqual(len(result['findings']), 2)
        self.assertEqual(result['tracked_files_checked'], 3)
        self.assertNotIn('path', result['findings'][0])
        self.assertNotIn('super-secret', json.dumps(result))
        self.assertNotIn('sensitive-value', json.dumps(result))

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

    def test_output_limit_stops_large_git_index_listing(self):
        # Exercise the real Git pipe with a tiny cap: no full output is buffered.
        for number in range(12):
            self.add(f'file-{number:02d}-long-filename.txt')
        with patch('devpilot.secret_audit.MAX_OUTPUT', 64):
            with self.assertRaisesRegex(RuntimeError, '8 MiB safety limit'):
                audit(self.root)

    def test_output_just_under_limit_is_complete(self):
        self.add('.env')
        self.add('README.md')
        raw = subprocess.run(['git', 'ls-files', '-z'], cwd=self.root, check=True,
                             capture_output=True).stdout
        with patch('devpilot.secret_audit.MAX_OUTPUT', len(raw)):
            result = audit(self.root)
        self.assertEqual(result['tracked_files_checked'], 2)
        self.assertEqual(result['findings'][0]['path'], '.env')

    def test_missing_directory(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.root / 'missing')]), 2)


if __name__ == '__main__':
    unittest.main()
