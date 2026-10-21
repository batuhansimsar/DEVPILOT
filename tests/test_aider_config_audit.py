"""Aider config files may include API keys; both filename audits must notice."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class AiderConfigAuditTests(unittest.TestCase):
    def test_recognizes_aider_configs_in_both_audits(self):
        for name in (
            '.aider.conf.yml', '.aider.conf.yaml',
            'nested/.aider.conf.yml', r'WORKSPACE\.AIDER.CONF.YAML',
            '.aider.conf.yml.bak',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
                self.assertEqual(classify(name), 'potential credential file')

    def test_ignores_templates_and_unrelated_configs(self):
        for name in (
            '.aider.conf.yml.example', '.aider.conf.yaml.sample.bak',
            'docs/aider.conf.yml', 'config.yml', 'README.md',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))
                self.assertIsNone(classify(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_configs_reported_and_values_not_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            tracked = ('.aider.conf.yml', '.aider.conf.yaml.example', 'src/config.yml')
            for name in (*tracked, 'untracked/.aider.conf.yaml'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('PRIVATE_TEST_API_KEY', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *tracked], check=True)
            simple = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)
        self.assertEqual(simple['candidates'], ['.aider.conf.yml'])
        self.assertEqual(len(detailed['findings']), 1)
        self.assertNotIn('path', detailed['findings'][0])
        self.assertNotIn('PRIVATE_TEST_API_KEY', repr(simple) + repr(detailed))


if __name__ == '__main__':
    unittest.main()
