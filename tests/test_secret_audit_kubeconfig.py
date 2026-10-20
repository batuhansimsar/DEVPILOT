"""Kubernetes access bundles must not slip through tracked-file secret checks."""
import unittest
from devpilot.secret_audit import classify

class KubeconfigClassificationTests(unittest.TestCase):
    def test_credential_file_names_and_backups(self):
        for name in ('kubeconfig', 'kubeconfig.yaml', 'kubeconfig.yml',
                     'cluster/KUBECONFIG.YAML', 'deploy/kubeconfig.backup'):
            with self.subTest(name=name):
                self.assertEqual(classify(name), 'potential credential file')

    def test_templates_are_not_flagged(self):
        for name in ('kubeconfig.example', 'kubeconfig.yaml.sample',
                     'kubeconfig.yml.template', 'docs/kubeconfig.yaml.dist'):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))

    def test_unrelated_kubernetes_docs_are_not_flagged(self):
        for name in ('docs/kubeconfig.md', 'deploy/kubeconfig.schema.json',
                     'kubeconfig_generator.py'):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))

if __name__ == '__main__':
    unittest.main()
