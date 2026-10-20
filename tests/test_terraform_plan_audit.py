"""Regressions for saved Terraform plan files in Git index secret audits."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class TerraformPlanClassificationTests(unittest.TestCase):
    def test_saved_plans_are_sensitive(self):
        for path in (
            'tfplan', 'infra/tfplan', 'infra/prod.tfplan',
            'TFPLAN', 'infra/prod.tfplan.bak', 'infra/prod.tfplan.backup',
            r'infra\prod.tfplan', 'prod.tfplan.old',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential Terraform plan containing secrets')

    def test_templates_and_unrelated_files_are_not_flagged(self):
        for path in (
            'infra/prod.tfplan.example', 'tfplan.sample', 'plan.md',
            'terraform.tfstate.example', 'infra/application.plan',
            'prod.tfplan.template.bak',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))


@unittest.skipUnless(shutil.which('git'), 'Git not available')
class TrackedTerraformPlanTests(unittest.TestCase):
    def test_audit_reports_saved_plans_without_reading_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for name in ('infra/production.tfplan', 'infra/test.tfplan.example'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('SENSITIVE_VALUE_NEVER_LOG', encoding='utf-8')
                subprocess.run(['git', 'add', '--', name], cwd=root, check=True)
            (root / 'unstaged.tfplan').write_text('NOT_TRACKED', encoding='utf-8')
            report = audit(root, redact_paths=True)
        self.assertFalse(report['ok'])
        self.assertEqual(report['tracked_files_checked'], 2)
        self.assertEqual(len(report['findings']), 1)
        self.assertEqual(report['findings'][0]['category'], 'potential Terraform plan containing secrets')
        self.assertNotIn('path', report['findings'][0])
        self.assertNotIn('SENSITIVE_VALUE_NEVER_LOG', json.dumps(report))
        self.assertNotIn('unstaged.tfplan', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
