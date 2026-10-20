"""Actual Vim swap names must be audited without reporting harmless files."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify
from devpilot.audit import _potential_secret, audit_tracked_files


class VimCredentialSwapTests(unittest.TestCase):
    def test_vim_swap_names_and_backup_chains(self):
        sensitive = (
            '.credentials.json.swp', '..pgpass.swo',
            '.auth.json.swn', '.credentials.json.swp.bak',
            '.config/pypoetry/.auth.toml.swp',
            '.config/pip/.pip.conf.swp',
            '.terraformrc.swn',
        )
        for path in sensitive:
            with self.subTest(path=path):
                self.assertIsNotNone(classify(path))
                self.assertTrue(_potential_secret(path))

    def test_vim_swaps_of_templates_and_nonsensitive_files(self):
        for path in (
            'docs/.credentials.example.json.swp',
            'docs/..pgpass.example.swo',
            'docs/README.md.swn',
            'src/.auth.toml.swp',
            'docs/.env.example.swp',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    def test_git_index_reports_vim_swaps_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            staged = ('.credentials.json.swp', '..pgpass.swo',
                      'docs/README.md.swn', 'docs/.env.example.swp')
            for filename in (*staged, 'untracked/.auth.json.swp'):
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('PRIVATE_VALUE_NEVER_OUTPUT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *staged], check=True)
            standalone = audit(root, redact_paths=True)
            cli = audit_tracked_files(root)
            self.assertEqual(len(standalone['findings']), 2)
            self.assertEqual(cli['candidates'], ['..pgpass.swo', '.credentials.json.swp'])
            self.assertNotIn('PRIVATE_VALUE_NEVER_OUTPUT', str(standalone) + str(cli))
            self.assertTrue(all('path' not in entry for entry in standalone['findings']))


if __name__ == '__main__':
    unittest.main()
