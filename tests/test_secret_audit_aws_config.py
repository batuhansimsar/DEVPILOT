"""AWS shared config files can include credentials; audit their tracked names."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, classify


class AWSConfigClassificationTests(unittest.TestCase):
    def test_aws_config_and_editor_backups_are_flagged(self):
        for name in (
            '.aws/config', 'nested/.aws/config',
            'PROFILE\\.AWS\\CONFIG', '.aws/config.bak',
            '.aws/config.~2~',
        ):
            with self.subTest(name=name):
                self.assertEqual(classify(name), 'potential credential configuration')

    def test_unrelated_and_template_configs_are_ignored(self):
        for name in (
            'config', 'docs/config', 'config/aws/config',
            '.aws/config.example', '.aws/config.template',
            '.aws/config.example.bak', '.aws/config.yml',
        ):
            with self.subTest(name=name):
                self.assertIsNone(classify(name))

    @unittest.skipUnless(shutil.which('git'), 'git is required for the index audit')
    def test_staged_aws_config_is_reported_without_reading_secret_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            config = root / '.aws' / 'config'
            config.parent.mkdir()
            config.write_text('aws_secret_access_key=never_report_this_value\n', encoding='utf-8')
            (root / 'config').write_text('non-sensitive settings\n', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '.aws/config', 'config'], check=True)
            report = audit(root, redact_paths=True)
        self.assertFalse(report['ok'])
        self.assertEqual(report['tracked_files_checked'], 2)
        self.assertEqual(len(report['findings']), 1)
        self.assertEqual(report['findings'][0]['category'], 'potential credential configuration')
        self.assertNotIn('path', report['findings'][0])
        self.assertNotIn('never_report_this_value', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
