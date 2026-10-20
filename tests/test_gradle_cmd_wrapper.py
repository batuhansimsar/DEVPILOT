"""Regression tests for .cmd Gradle wrapper fallback on Windows."""

import tempfile
import unittest
from pathlib import Path

from devpilot.gradle import gradle_test_command


class GradleCmdWrapperTests(unittest.TestCase):
    def test_cmd_wrapper_is_usable_without_bat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'GradleW.CmD').write_text('@echo off\n')
            self.assertEqual(
                gradle_test_command(root, {'GradleW.CmD'}, 'nt'),
                ([r'.\GradleW.CmD', 'test'], 'Gradle Windows wrapper'),
            )

    def test_bat_has_priority_when_both_wrappers_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gradlew.bat').write_text('@echo off\n')
            (root / 'gradlew.cmd').write_text('@echo off\n')
            self.assertEqual(
                gradle_test_command(root, {'gradlew.bat', 'gradlew.cmd'}, 'nt')[0],
                [r'.\gradlew.bat', 'test'],
            )

    def test_cmd_must_be_regular_file_not_link(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'gradlew.cmd'
            target.write_text('@echo off\n')
            try:
                (root / 'gradlew.cmd').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(gradle_test_command(root, {'gradlew.cmd'}, 'nt')[0], ['gradle', 'test'])

    def test_unrelated_cmd_script_is_never_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gradlew.cmd.txt').write_text('')
            self.assertEqual(gradle_test_command(root, {'gradlew.cmd.txt'}, 'nt')[0], ['gradle', 'test'])


if __name__ == '__main__':
    unittest.main()
