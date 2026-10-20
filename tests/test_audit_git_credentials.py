"""Git and GitHub CLI plaintext credential storage detection regressions."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files


class GitCredentialAuditTests(unittest.TestCase):
    def test_recognizes_git_and_gh_credential_storage_locations(self):
        for path in (
            '.git-credentials', 'nested/.git-credentials',
            '.config/gh/hosts.yml', '.config/gh/hosts.yaml',
            'nested/gh/hosts.yml', 'GH\\HOSTS.YML',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))

    def test_generic_hosts_files_and_templates_are_not_flagged(self):
        for path in (
            'docs/hosts.yml', 'src/hosts.yaml', 'gh/hosts.yml.example',
            '.git-credentials.example', 'docs/git-credentials.txt',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_reads_only_git_index_and_never_exposes_credential_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True, capture_output=True)
            paths = (
                'nested/.git-credentials', '.config/gh/hosts.yml',
                'docs/hosts.yml', 'gh/hosts.yml.example',
            )
            for name in paths:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('fake-secret-must-not-be-reported', encoding='utf-8')
            # An untracked credential-like name must not be included.
            (root / 'other.git-credentials').write_text('fake-secret-must-not-be-reported')
            subprocess.run(['git', 'add', '--', *paths], cwd=root, check=True, capture_output=True)
            result = audit_tracked_files(root)
            self.assertNotIn('error', result)
            self.assertEqual(result['tracked_files'], 4)
            self.assertEqual(result['candidates'], ['.config/gh/hosts.yml', 'nested/.git-credentials'])
            self.assertNotIn('fake-secret-must-not-be-reported', str(result))


if __name__ == '__main__':
    unittest.main()
