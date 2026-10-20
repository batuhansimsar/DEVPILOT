"""Regression coverage for Terraform filenames that can expose credentials."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from devpilot.audit import _potential_secret, audit_tracked_files

class TerraformAuditTests(unittest.TestCase):
    def test_sensitive_terraform_names(self):
        for name in ('terraform.tfstate', 'terraform.tfstate.backup', 'prod.tfvars',
                     'staging.auto.tfvars', 'secrets.tfvars.json', 'nested/MAIN.TFSTATE'):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_terraform_templates_are_not_flagged(self):
        for name in ('terraform.tfvars.example', 'staging.tfvars.sample',
                     'secrets.tfvars.json.template', 'main.tf', 'providers.tf'):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_only_git_tracked_terraform_files_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            for name in ('terraform.tfstate', 'vars.tfvars', 'vars.tfvars.example', 'untracked.auto.tfvars'):
                (root / name).write_text('placeholder\n')
            subprocess.run(['git', 'add', '--', 'terraform.tfstate', 'vars.tfvars', 'vars.tfvars.example'],
                           cwd=root, check=True)
            report = audit_tracked_files(root)
            self.assertEqual(report['candidates'], ['terraform.tfstate', 'vars.tfvars'])
            self.assertEqual(report['tracked_files'], 3)

if __name__ == '__main__':
    unittest.main()
