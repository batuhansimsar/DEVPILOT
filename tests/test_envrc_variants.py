"""Direnv environment overrides should not evade tracked-filename audits."""

import unittest

from devpilot.audit import _potential_secret
from devpilot.envrc import is_sensitive_direnv_file
from devpilot.secret_audit import classify


class DirenvVariantAuditTests(unittest.TestCase):
    def test_recognize_direnv_overrides(self):
        for name in ('.envrc', '.envrc.local', '.envrc.production', '.envrc.example.local'):
            with self.subTest(name=name):
                self.assertTrue(is_sensitive_direnv_file(name))

    def test_ignore_template_variants(self):
        for name in ('.envrc.example', '.envrc.sample', '.envrc.template',
                     '.envrc.dist', '.envrc.defaults', '.envrcx.local', 'README.md'):
            with self.subTest(name=name):
                self.assertFalse(is_sensitive_direnv_file(name))

    def test_both_auditors_flag_sensitive_variants_and_backups(self):
        for path in ('config/.envrc.local', '.envrc.production',
                     'nested/.envrc.local.bak.old', 'project\\.ENVRC.EXAMPLE.LOCAL'):
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    def test_both_auditors_ignore_templates_and_unrelated_names(self):
        for path in ('config/.envrc.example', '.envrc.sample.bak',
                     'nested/.envrc.template.old', 'src/.envrcx.local'):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))


if __name__ == '__main__':
    unittest.main()
