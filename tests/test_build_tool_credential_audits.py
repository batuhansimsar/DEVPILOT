"""Build-tool credential configuration paths must be caught by both audit entrypoints."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.audit import _potential_secret, audit_tracked_files
from devpilot.secret_audit import audit, classify


class BuildToolCredentialAuditTests(unittest.TestCase):
    def test_build_tool_credentials_are_flagged(self):
        cases = (
            'project/.m2/settings.xml',
            '.gradle/gradle.properties',
            'AppData\\NuGet\\NuGet.Config',
            'home/.m2/settings.xml.bak',
            'home/NuGet/NuGet.Config.swp',
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential configuration')
                self.assertTrue(_potential_secret(path))

    def test_generic_configs_and_templates_are_not_flagged(self):
        cases = (
            'docs/settings.xml',
            'service/gradle.properties',
            'project/NuGet.Config',
            '.m2/settings.xml.example',
            '.gradle/gradle.properties.sample',
            'NuGet/NuGet.Config.template.bak',
        )
        for path in cases:
            with self.subTest(path=path):
                self.assertIsNone(classify(path))
                self.assertFalse(_potential_secret(path))

    @unittest.skipUnless(shutil.which('git'), 'git required')
    def test_git_index_audits_report_only_tracked_paths_without_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            tracked = (
                '.m2/settings.xml',
                '.gradle/gradle.properties',
                'NuGet/NuGet.Config',
                'docs/settings.xml',
                '.m2/settings.xml.example',
            )
            for name in (*tracked, 'other/.m2/settings.xml'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('SECRET_DO_NOT_DISCLOSE', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '--', *tracked], check=True)
            standalone = audit(root)
            cli = audit_tracked_files(root)
        expected = ['.gradle/gradle.properties', '.m2/settings.xml', 'NuGet/NuGet.Config']
        self.assertEqual(standalone['tracked_files_checked'], len(tracked))
        self.assertEqual(sorted(row['path'] for row in standalone['findings']), expected)
        self.assertEqual(cli['candidates'], expected)
        self.assertNotIn('SECRET_DO_NOT_DISCLOSE', str(standalone))
        self.assertNotIn('SECRET_DO_NOT_DISCLOSE', str(cli))


if __name__ == '__main__':
    unittest.main()
