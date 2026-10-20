"""Terraform outputs with additional suffixes must not evade the Git audit."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class TerraformQualifiedFilesTests(unittest.TestCase):
    def test_sensitive_qualified_names(self):
        for path in (
            'production.tfvars.local', 'infra/prod.tfvars.json.production',
            'terraform.tfstate.1680000000', 'prod.tfplan.json',
            'tfplan.production', 'vars.tfvars.example.local',
            'vars.tfvars.json.sample.production', 'vars.tfvars.local.bak',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_templates_and_unrelated_files_not_flagged(self):
        for path in (
            'production.tfvars.example', 'vars.tfvars.json.template',
            'terraform.tfvars.defaults', 'tfplan.example',
            'terraform.tf', 'README.md', 'vars.tfvars.example.old',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_git_index_identifies_qualified_terraform_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('prod.tfvars.local', 'prod.tfvars.example',
                         'terraform.tfstate.1234', 'tfplan.json'):
                (root / name).write_text('placeholder\n', encoding='utf-8')
            subprocess.run(['git', 'add', 'prod.tfvars.local', 'prod.tfvars.example',
                            'terraform.tfstate.1234', 'tfplan.json'],
                           cwd=root, check=True)
            report = audit_tracked_files(root)
            self.assertNotIn('error', report)
            self.assertEqual(report['tracked_files'], 4)
            self.assertEqual(report['candidates'], [
                'prod.tfvars.local', 'terraform.tfstate.1234', 'tfplan.json',
            ])


if __name__ == '__main__':
    unittest.main()
