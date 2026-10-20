"""Workspace discovery for Gradle Groovy and Kotlin settings files."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class GradleSettingsWorkspaceTests(unittest.TestCase):
    def test_groovy_settings_without_build_gradle(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'settings.gradle').write_text("rootProject.name = 'single'\n")
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['path'], '.')
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Java'])
        self.assertEqual(report['workspaces'][0]['manifests'],
                         [{'file': 'settings.gradle', 'ecosystem': 'Java'}])

    def test_kotlin_settings_in_nested_project(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / 'apps' / 'android'
            nested.mkdir(parents=True)
            (nested / 'settings.gradle.kts').write_text('rootProject.name = "android"\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['path'], 'apps/android')
        self.assertEqual(report['workspaces'][0]['manifests'],
                         [{'file': 'settings.gradle.kts', 'ecosystem': 'Java'}])

    def test_multiple_gradle_manifests_are_one_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('settings.gradle', 'build.gradle', 'settings.gradle.kts'):
                (root / name).write_text('// local only\n')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Java'])
        self.assertEqual([m['file'] for m in report['workspaces'][0]['manifests']],
                         ['build.gradle', 'settings.gradle', 'settings.gradle.kts'])

    def test_symlink_to_external_settings_is_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as external:
            root = Path(temp)
            target = Path(external) / 'settings.gradle'
            target.write_text('include(":app")\n')
            try:
                (root / 'settings.gradle').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
