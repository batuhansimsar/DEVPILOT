"""Terraform filename regressions for the standalone secret audit command."""
import unittest
from devpilot.secret_audit import classify

class TerraformSecretClassificationTests(unittest.TestCase):
    def test_terraform_variable_files_flagged(self):
        for name in ('terraform.tfvars', 'env/prod.auto.tfvars', 'vars.tfvars.json',
                     'vars.TFVARS', 'terraform.tfstate', 'terraform.tfstate.backup'):
            with self.subTest(name=name):
                self.assertIn('Terraform', classify(name))

    def test_template_variable_files_not_flagged(self):
        for name in ('terraform.tfvars.example', 'vars.tfvars.sample',
                     'secrets.tfvars.json.template', 'staging.tfvars.dist',
                     'env/tfvars.json', 'main.tf'):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))

if __name__ == '__main__':
    unittest.main()
