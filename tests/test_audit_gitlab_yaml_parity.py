"""Security regression: GitLab CLI config.yaml is a credential-bearing path."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class GitLabYAMLParityTests(unittest.TestCase):
    def test_both_auditors_classify_yaml_and_backups(self):
        for name in (
            '.config/glab-cli/config.yaml',
            'home/glab-cli/config.yaml',
            r'Users\me\.config\glab-cli\CONFIG.YAML',
            '.config/glab-cli/config.yaml.bak',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
                self.assertEqual(classify(name), 'potential credential configuration')

    def test_public_filenames_and_templates_remain_safe(self):
        for name in (
            'docs/config.yaml',
            '.config/glab-cli/config.yaml.example',
            '.config/glab-cli/config.yml.template',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))
                self.assertIsNone(classify(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_git_index_audits_detect_yaml_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            config = root / '.config/glab-cli/config.yaml'
            config.parent.mkdir(parents=True)
            config.write_text('token: NEVER_PRINT_THIS_TEST_VALUE', encoding='utf-8')
            (root / 'README.md').write_text('safe', encoding='utf-8')
            subprocess.run(
                ['git', 'add', '--', '.config/glab-cli/config.yaml', 'README.md'],
                cwd=root, check=True,
            )
            primary = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)
        self.assertNotIn('error', primary)
        self.assertEqual(primary['candidates'], ['.config/glab-cli/config.yaml'])
        self.assertEqual(primary['tracked_files'], 2)
        self.assertEqual(len(detailed['findings']), 1)
        self.assertNotIn('path', detailed['findings'][0])
        self.assertNotIn('NEVER_PRINT_THIS_TEST_VALUE', repr(primary))
        self.assertNotIn('NEVER_PRINT_THIS_TEST_VALUE', repr(detailed))


if __name__ == '__main__':
    unittest.main()
