"""Regression tests for standalone tracked-secret filename classification."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class TerraformSecretAuditTests(unittest.TestCase):
    def test_terraform_variable_files_are_sensitive(self):
        for path in ('terraform.tfvars', 'environments/prod.auto.tfvars', 'vars.auto.tfvars.json'):
            with self.subTest(path=path):
                self.assertIn('Terraform', classify(path))

    def test_distribution_and_example_files_are_safe(self):
        for path in ('.env.dist', '.env.prod.dist', '.env.defaults', 'vars.tfvars.example', '.envrc.sample'):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    def test_only_tracked_sensitive_names_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for name in ('production.tfvars', 'production.tfvars.example', '.env.dist'):
                (root / name).write_text('placeholder', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--',
                            'production.tfvars', 'production.tfvars.example', '.env.dist'], check=True)
            (root / 'untracked.tfvars').write_text('placeholder', encoding='utf-8')
            report = audit(root)
            self.assertEqual([item['path'] for item in report['findings']], ['production.tfvars'])
            self.assertEqual(report['tracked_files_checked'], 3)


if __name__ == '__main__':
    unittest.main()
