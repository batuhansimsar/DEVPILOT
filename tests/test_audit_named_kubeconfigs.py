"""Detect tracked kubeconfig files with conventional project-specific filenames."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import classify


class NamedKubeconfigAuditTests(unittest.TestCase):
    def test_named_kubeconfigs_and_backups_flagged_by_both_audits(self):
        for path in (
            'prod.kubeconfig', 'clusters/staging.kubeconfig.yaml',
            'clusters/dev.kubeconfig.yml', r'WORK\PROD.KUBECONFIG',
            'prod.kubeconfig.bak', 'staging.kubeconfig.yaml.~2~',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential Kubernetes credential configuration')

    def test_templates_and_unrelated_yaml_are_not_flagged(self):
        for path in (
            'docs/deployment.yaml', 'config.yml', 'cluster.config',
            'prod.kubeconfig.example', 'prod.kubeconfig.yaml.template',
            'prod.kubeconfig.yml.sample.bak',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is required')
    def test_git_index_flags_named_config_without_exposing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            paths = {
                'cluster/prod.kubeconfig': 'token: NEVER_PRINT_KUBE_TOKEN',
                'cluster/prod.kubeconfig.example': 'placeholder',
                'cluster/readme.yml': 'public information',
            }
            for name, content in paths.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *paths], check=True)
            report = audit_tracked_files(root)
        self.assertNotIn('error', report)
        self.assertEqual(report['tracked_files'], 3)
        self.assertEqual(report['candidates'], ['cluster/prod.kubeconfig'])
        self.assertNotIn('NEVER_PRINT_KUBE_TOKEN', repr(report))


if __name__ == '__main__':
    unittest.main()
