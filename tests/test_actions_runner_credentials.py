"""A self-hosted Actions runner's local registration files must not be committed."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.runner_credentials import is_actions_runner_credential_location
from devpilot.secret_audit import audit, classify


class ActionsRunnerCredentialTests(unittest.TestCase):
    def test_private_runner_files_and_editor_backups(self):
        paths = (
            'actions-runner/.credentials',
            'ci/actions-runner/.credentials_rsaparams',
            '.actions-runner/.credentials',
            r'CI\ACTIONS-RUNNER\.CREDENTIALS_RSAPARAMS',
            'actions-runner/.credentials_rsaparams.bak.old',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential GitHub Actions runner credentials')

    def test_unrelated_files_and_templates_are_not_flagged(self):
        paths = (
            '.credentials',
            'other/.credentials_rsaparams',
            'actions-runner/.runner',
            'actions-runner/logs/.credentials',
            'actions-runner/.credentials.example',
            'actions-runner/.credentials_rsaparams.sample.bak',
            'actions-runner/README.md',
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_helper_requires_conventional_installation_directory(self):
        self.assertTrue(is_actions_runner_credential_location(
            ('ci', 'actions-runner', '.credentials_rsaparams')))
        self.assertFalse(is_actions_runner_credential_location(
            ('ci', 'docs', '.credentials_rsaparams')))

    @unittest.skipUnless(shutil.which('git'), 'Git required')
    def test_tracked_only_and_redacted_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            sensitive = ('actions-runner/.credentials', 'actions-runner/.credentials_rsaparams')
            safe = ('actions-runner/README.md', 'actions-runner/.credentials.example')
            for relative in (*sensitive, *safe, 'other/actions-runner/.credentials'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PRIVATE_TEST_VALUE_DO_NOT_PRINT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *sensitive, *safe],
                           cwd=root, check=True, capture_output=True)
            basic = audit_tracked_files(root)
            redacted = audit(root, redact_paths=True)

        self.assertNotIn('error', basic)
        self.assertEqual(basic['tracked_files'], 4)
        self.assertEqual(basic['candidates'], list(sensitive))
        self.assertEqual(redacted['tracked_files_checked'], 4)
        self.assertEqual(len(redacted['findings']), 2)
        self.assertTrue(all(
            finding['category'] == 'potential GitHub Actions runner credentials'
            and 'path' not in finding for finding in redacted['findings']))
        self.assertNotIn('PRIVATE_TEST_VALUE_DO_NOT_PRINT', repr(basic))
        self.assertNotIn('PRIVATE_TEST_VALUE_DO_NOT_PRINT', repr(redacted))
        self.assertNotIn('other/actions-runner', repr(basic))


if __name__ == '__main__':
    unittest.main()
