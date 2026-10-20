"""Regression tests for credential-bearing build-tool configuration paths."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class BuildToolCredentialsTests(unittest.TestCase):
    def test_both_auditors_detect_build_tool_credentials_and_backups(self):
        for path in (
            '.m2/settings.xml',
            r'HOME\.M2\SETTINGS.XML',
            '.m2/settings-security.xml',
            'home/.m2/settings-security.xml.bak',
            '.gradle/gradle.properties',
            'home/.gradle/gradle.properties.old',
            'nuget/NuGet.Config',
            'packages/nuget/nuget.config.bak',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential credential configuration')

    def test_unrelated_files_and_templates_are_not_flagged(self):
        for path in (
            'docs/settings.xml', 'src/gradle.properties', 'nuget.config',
            '.m2/settings.xml.example', '.m2/settings-security.xml.template',
            '.gradle/gradle.properties.sample', 'nuget/nuget.config.dist',
            'README.md',
        ):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    @unittest.skipUnless(shutil.which('git'), 'Git executable required')
    def test_only_tracked_build_tool_credentials_are_reported_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            credentials = (
                '.m2/settings.xml', '.m2/settings-security.xml',
                '.gradle/gradle.properties', 'packages/nuget/NuGet.Config',
            )
            other = ('docs/settings.xml', '.m2/settings.xml.example', 'src/gradle.properties')
            for relative in (*credentials, *other, 'untracked/.m2/settings.xml'):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('PRIVATE_FIXTURE_VALUE_NOT_FOR_LOGS', encoding='utf-8')
            subprocess.run(['git', 'add', '--', *credentials, *other],
                           cwd=root, check=True, capture_output=True)
            basic = audit_tracked_files(root)
            detailed = audit(root, redact_paths=True)
        self.assertNotIn('error', basic)
        self.assertEqual(basic['tracked_files'], len(credentials) + len(other))
        self.assertEqual(basic['candidates'], sorted(credentials))
        self.assertEqual(detailed['tracked_files_checked'], len(credentials) + len(other))
        self.assertEqual(len(detailed['findings']), len(credentials))
        self.assertTrue(all('path' not in finding for finding in detailed['findings']))
        self.assertNotIn('PRIVATE_FIXTURE_VALUE_NOT_FOR_LOGS', repr(basic))
        self.assertNotIn('PRIVATE_FIXTURE_VALUE_NOT_FOR_LOGS', repr(detailed))


if __name__ == '__main__':
    unittest.main()
