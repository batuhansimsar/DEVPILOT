"""Regression tests for Terraform filenames with qualifiers after sensitive extensions."""

import unittest

from devpilot.secret_audit import classify


class TerraformVariantTests(unittest.TestCase):
    def test_sensitive_terraform_filename_variants(self):
        cases = {
            'infra/prod.tfvars.local': 'potential Terraform variables containing secrets',
            'infra/prod.tfvars.json.local': 'potential Terraform variables containing secrets',
            'infra/prod.tfvars.example.local': 'potential Terraform variables containing secrets',
            'infra/prod.tfvars.json.sample.production': 'potential Terraform variables containing secrets',
            'state/terraform.tfstate.local': 'potential Terraform state containing secrets',
            'state/terraform.tfstate.example.local': 'potential Terraform state containing secrets',
            'build/terraform.tfplan.local': 'potential Terraform plan containing secrets',
            'build/tfplan.example.local': 'potential Terraform plan containing secrets',
        }
        for path, category in cases.items():
            with self.subTest(path=path):
                self.assertEqual(classify(path), category)

    def test_templates_and_incidental_names_remain_safe(self):
        for path in (
            'infra/prod.tfvars.example',
            'infra/prod.tfvars.json.sample',
            'infra/prod.tfvars.json.template',
            'state/terraform.tfstate.example',
            'build/terraform.tfplan.example',
            'build/tfplan.example',
            'notes/terraform.tfstateful.md',
            'notes/terraform.tfvarslike',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))


if __name__ == '__main__':
    unittest.main()
