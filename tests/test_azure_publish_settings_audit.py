"""Detect exported Azure deployment credentials by filename only."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.publish_profiles import is_azure_publish_settings
from devpilot.secret_audit import audit, classify


class AzurePublishSettingsTests(unittest.TestCase):
    def test_filename_predicate(self):
        self.assertTrue(is_azure_publish_settings(('site.publishsettings',)))
        self.assertTrue(is_azure_publish_settings(('deploy', 'site.publishsettings')))
        self.assertFalse(is_azure_publish_settings(()))
        self.assertFalse(is_azure_publish_settings(('deploy', 'site.publishsettings.example')))
        self.assertFalse(is_azure_publish_settings(('deploy', 'publishsettings.xml')))

    def test_both_auditors_detect_exports_and_backups(self):
        for path in (
            'my-app.PublishSettings',
            'deployment/site.publishsettings',
            'DEPLOYMENT\\SITE.PUBLISHSETTINGS',
            'deployment/site.PublishSettings.bak',
            'deployment/site.publishsettings.old',
            'deployment/site.publishsettings.swp',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential Azure publish settings credentials')
                self.assertTrue(_potential_secret(path))

    def test_templates_and_similarly_named_documents_are_safe(self):
        for path in (
            'site.publishsettings.example',
            'site.publishsettings.sample.bak',
            'site.publishsettings.template',
            'site.publishsettings.dist',
            'site.publishsettings.defaults',
            'docs/publishsettings.md',
            'docs/my.publishsettings.xml',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_staged_exports_are_flagged_without_reading_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            fixtures = {
                'site.PublishSettings': 'SENSITIVE_PUBLISH_PASSWORD',
                'site.publishsettings.example': 'harmless example',
            }
            for name, contents in fixtures.items():
                (root / name).write_text(contents, encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', '.'], check=True)
            report = audit(root, redact_paths=True)
            self.assertEqual(report['tracked_files_checked'], 2)
            self.assertEqual(len(report['findings']), 1)
            self.assertEqual(report['findings'][0]['category'],
                             'potential Azure publish settings credentials')
            self.assertNotIn('SENSITIVE_PUBLISH_PASSWORD', json.dumps(report))
            self.assertNotIn('path', report['findings'][0])
            main_report = audit_tracked_files(root)
            self.assertEqual(main_report['candidates'], ['site.PublishSettings'])


if __name__ == '__main__':
    unittest.main()
