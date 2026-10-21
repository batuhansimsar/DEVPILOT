"""Keep both filename-only audits aligned for Azure Functions local secrets."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.azure_functions_settings import is_azure_functions_local_settings
from devpilot.secret_audit import audit, classify


class AzureFunctionsLocalSettingsTests(unittest.TestCase):
    def test_precise_filename_match(self):
        self.assertFalse(is_azure_functions_local_settings(()))
        self.assertTrue(is_azure_functions_local_settings(('functions', 'local.settings.json')))
        self.assertFalse(is_azure_functions_local_settings(('functions', 'settings.json')))

    def test_both_auditors_detect_live_files_and_editor_backups(self):
        for name in (
            'local.settings.json', 'functions/local.settings.json',
            'FUNCTIONS\\LOCAL.SETTINGS.JSON',
            'functions/local.settings.json.bak',
            'functions/local.settings.json.___jb_old___',
            'functions/.local.settings.json.swp',
        ):
            with self.subTest(name=name):
                self.assertEqual(classify(name), 'potential Azure Functions local settings credentials')
                self.assertTrue(_potential_secret(name))

    def test_templates_and_unrelated_names_are_not_flagged(self):
        for name in (
            'local.settings.json.example', 'local.settings.json.sample.bak',
            'local.settings.json.template', 'local.settings.json.dist',
            'local.settings.json.defaults', 'appsettings.json',
            'settings.json', 'docs/local.settings.json.md',
        ):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))
                self.assertFalse(_potential_secret(name))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_staged_local_settings_reported_without_opening_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            files = {
                'local.settings.json': '{"Values": {"Storage": "PRIVATE_LOCAL_STORAGE_KEY"}}',
                'local.settings.json.example': '{"Values": {"Storage": "use-development-values"}}',
                'README.md': 'safe',
            }
            for name, contents in files.items():
                (root / name).write_text(contents, encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            report = audit(root, redact_paths=True)
            self.assertEqual(report['tracked_files_checked'], 3)
            self.assertEqual(len(report['findings']), 1)
            self.assertEqual(report['findings'][0]['category'],
                             'potential Azure Functions local settings credentials')
            self.assertNotIn('path', report['findings'][0])
            self.assertNotIn('PRIVATE_LOCAL_STORAGE_KEY', json.dumps(report))
            basic = audit_tracked_files(root)
            self.assertEqual(basic['candidates'], ['local.settings.json'])
            self.assertNotIn('PRIVATE_LOCAL_STORAGE_KEY', repr(basic))


if __name__ == '__main__':
    unittest.main()
