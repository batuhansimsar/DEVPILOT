"""Regression tests for Terraform CLI credentials filename handling."""
import unittest
from devpilot.secret_audit import classify


class TerraformCredentialsTests(unittest.TestCase):
    def test_terraform_cli_credentials_are_sensitive(self):
        for name in (
            '.terraform.d/credentials.tfrc.json',
            'home/user/.terraform.d/credentials.tfrc.json',
            'HOME\\.TERRAFORM.D\\CREDENTIALS.TFRC.JSON',
            '.terraform.d/credentials.tfrc.json.bak',
        ):
            with self.subTest(name=name):
                self.assertEqual(classify(name), 'potential credential configuration')

    def test_unrelated_and_template_files_ignored(self):
        for name in (
            'docs/credentials.tfrc.json',
            '.terraform.d/credentials.tfrc.json.example',
            '.terraform.d/credentials.tfrc.json.sample',
            'terraform/README.md',
        ):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))


if __name__ == '__main__':
    unittest.main()
