"""Regression tests for Terraform and Google Cloud CLI credential filenames."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class CloudCLICredentialAuditTests(unittest.TestCase):
    def test_recognizes_terraform_and_gcloud_credential_files(self):
        for path in (
            '.terraformrc', 'nested/.terraformrc',
            '.terraform.d/credentials.tfrc.json',
            '.config/gcloud/credentials.db',
            '.config/gcloud/access_tokens.db',
            r'.config\gcloud\credentials.db',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_ignores_generic_databases_and_sample_files(self):
        for path in (
            'docs/credentials.db', 'docs/access_tokens.db',
            'docs/gcloud/credentials.db.example',
            '.terraformrc.example', 'credentials.tfrc.json.sample',
            'docs/terraform.tfrc',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_detects_staged_credentials_without_reading_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            paths = (
                '.terraformrc', '.terraform.d/credentials.tfrc.json',
                '.config/gcloud/credentials.db', 'docs/credentials.db',
            )
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('never-include-this-secret-in-output', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True, capture_output=True)
            report = audit_tracked_files(root)
            self.assertEqual(report['tracked_files'], len(paths))
            self.assertEqual(report['candidates'], sorted(paths[:3]))
            self.assertNotIn('never-include-this-secret-in-output', str(report))


if __name__ == '__main__':
    unittest.main()
