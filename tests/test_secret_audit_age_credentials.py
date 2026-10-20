"""Regression tests for private age/SOPS identity filenames in the Git index."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.age_credentials import is_age_identity_path
from devpilot.secret_audit import audit, classify


class AgeIdentityPathTests(unittest.TestCase):
    def test_conventional_identity_locations(self):
        for path in (
            '.config/sops/age/keys.txt',
            'home/.config/sops/age/keys.txt',
            'HOME\\.CONFIG\\AGE\\KEYS.TXT',
            '.config/age/keys.txt.bak',
            'src/.config/sops/age/keys.txt.swp',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential age private identity file')

    def test_templates_and_unrelated_keys_txt_are_not_flagged(self):
        for path in (
            'docs/keys.txt', 'src/age/keys.txt',
            '.config/sops/keys.txt', '.config/sops/age/notes.txt',
            '.config/age/keys.txt.example',
            '.config/sops/age/keys.txt.template.bak',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))

    def test_path_classifier_requires_complete_suffix(self):
        self.assertTrue(is_age_identity_path(('.config', 'sops', 'age', 'keys.txt')))
        self.assertFalse(is_age_identity_path(('docs', 'age', 'keys.txt')))
        self.assertFalse(is_age_identity_path(('keys.txt',)))


@unittest.skipUnless(shutil.which('git'), 'Git executable required')
class GitIndexAgeIdentityTests(unittest.TestCase):
    def test_stage_age_identity_without_exposing_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            identity = '.config/sops/age/keys.txt'
            target = root / identity
            target.parent.mkdir(parents=True)
            target.write_text('AGE-SECRET-KEY-NEVER-REPORT', encoding='utf-8')
            subprocess.run(['git', 'add', '--', identity], cwd=root, check=True, capture_output=True)
            report = audit(root)
            self.assertEqual(report['tracked_files_checked'], 1)
            self.assertEqual(report['findings'][0]['category'], 'potential age private identity file')
            self.assertEqual(report['findings'][0]['path'], identity)
            self.assertNotIn('AGE-SECRET-KEY-NEVER-REPORT', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
