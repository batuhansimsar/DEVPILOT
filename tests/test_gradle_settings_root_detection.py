"""Gradle settings-only projects must appear in root project diagnostics."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core


class GradleSettingsRootDetectionTests(unittest.TestCase):
    def test_settings_only_roots_are_recognized_without_guessing_test_tasks(self):
        for name in ('settings.gradle', 'settings.gradle.kts'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('rootProject.name = "demo"\n', encoding='utf-8')

                self.assertIn('Java', core.detect_projects(root))
                report = core.analyze_project(root)
                self.assertIn('Java', report['project_types'])
                self.assertIn(name, report['key_files'])
                # Settings files alone do not guarantee a Gradle test task.
                self.assertFalse(any(
                    command['ecosystem'] == 'Java'
                    for command in core.test_commands(root)
                ))

                with patch('devpilot.core.shutil.which', return_value=None):
                    doctor = core.doctor_report(root)
                self.assertIn('Missing java required by detected project',
                              doctor['warnings'])

    def test_symlinked_settings_does_not_create_a_project(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'settings.gradle'
            target.write_text('// external', encoding='utf-8')
            try:
                (root / 'settings.gradle').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Java', core.detect_projects(root))
            self.assertNotIn('settings.gradle', core.analyze_project(root)['key_files'])


if __name__ == '__main__':
    unittest.main()
