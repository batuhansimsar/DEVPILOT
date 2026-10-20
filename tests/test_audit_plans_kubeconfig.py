"""Git filename audit must flag tracked Terraform plans and Kubernetes configs."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class PlanAndKubeconfigAuditTests(unittest.TestCase):
    def test_sensitive_plan_and_kubeconfig_filenames(self):
        for name in (
            'tfplan', 'infra/prod.tfplan', 'infra/prod.tfplan.bak',
            'kubeconfig', 'config/kubeconfig.yml', 'KUBECONFIG.YAML',
            'kubeconfig.old',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))

    def test_samples_and_normal_files_are_not_flagged(self):
        for name in (
            'kubeconfig.yaml.example', 'infra/prod.tfplan.example',
            'docs/plan.md', 'src/config.yml', 'plan.tf',
            '.env.example.bak',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_sensitive_names_appear_without_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            names = ('tfplan', 'infra/release.tfplan', 'kubeconfig.yaml',
                     'kubeconfig.yaml.example', 'infra/release.tfplan.example')
            for name in (*names, 'untracked.tfplan'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('SECRET_SHOULD_NOT_APPEAR', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *names], check=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], len(names))
        self.assertEqual(report['candidates'],
                         ['infra/release.tfplan', 'kubeconfig.yaml', 'tfplan'])
        self.assertNotIn('SECRET_SHOULD_NOT_APPEAR', str(report))
        self.assertNotIn('untracked.tfplan', str(report))


if __name__ == '__main__':
    unittest.main()
