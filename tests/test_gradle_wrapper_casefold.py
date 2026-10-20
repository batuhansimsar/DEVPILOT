"""Regression tests for case-insensitive Gradle wrapper discovery on Windows."""

import tempfile
import unittest
from pathlib import Path

from devpilot.gradle import gradle_test_command


class GradleWindowsWrapperCaseTests(unittest.TestCase):
    def test_uppercase_windows_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'GRADLEW.BAT').write_text('@echo off\n')
            cmd, reason = gradle_test_command(root, {'GRADLEW.BAT'}, 'nt')
            self.assertEqual(cmd, [r'.\GRADLEW.BAT', 'test'])
            self.assertEqual(reason, 'Gradle Windows wrapper')

    def test_mixed_case_windows_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'GradleW.Bat').write_text('@echo off\n')
            self.assertEqual(gradle_test_command(root, {'GradleW.Bat'}, 'nt')[0],
                             [r'.\GradleW.Bat', 'test'])

    def test_nonwrapper_file_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'GRADLEW.BAT.txt').write_text('')
            self.assertEqual(gradle_test_command(root, {'GRADLEW.BAT.txt'}, 'nt')[0],
                             ['gradle', 'test'])

    def test_linked_uppercase_wrapper_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            target = Path(outside) / 'wrapper.bat'
            target.write_text('')
            try:
                (root / 'GRADLEW.BAT').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(gradle_test_command(root, {'GRADLEW.BAT'}, 'nt')[0],
                             ['gradle', 'test'])


if __name__ == '__main__':
    unittest.main()
