"""Tests for safe Gradle wrapper detection on Windows and POSIX."""

import os
import tempfile
import unittest
from pathlib import Path

from devpilot.gradle import gradle_test_command
from devpilot import core


class GradleDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'build.gradle').write_text('')

    def test_no_wrapper_uses_installed_gradle(self):
        self.assertEqual(gradle_test_command(self.root, set(), 'posix')[0], ['gradle', 'test'])
        self.assertEqual(gradle_test_command(self.root, set(), 'nt')[0], ['gradle', 'test'])

    def test_posix_wrapper_must_be_executable(self):
        script = self.root / 'gradlew'
        script.write_text('#!/bin/sh\n')
        if os.name == 'nt':
            self.skipTest('POSIX mode bits not supported on Windows')
        script.chmod(0o644)
        self.assertEqual(gradle_test_command(self.root, {'gradlew'}, 'posix')[0], ['gradle', 'test'])
        script.chmod(0o755)
        self.assertEqual(gradle_test_command(self.root, {'gradlew'}, 'posix')[0], ['./gradlew', 'test'])
        self.assertEqual(core.test_commands(self.root)[0]['argv'], ['./gradlew', 'test'])

    def test_windows_needs_bat_not_unix_wrapper(self):
        (self.root / 'gradlew').write_text('')
        self.assertEqual(gradle_test_command(self.root, {'gradlew'}, 'nt')[0], ['gradle', 'test'])
        (self.root / 'gradlew.bat').write_text('@echo off\n')
        self.assertEqual(gradle_test_command(self.root, {'gradlew', 'gradlew.bat'}, 'nt')[0],
                         [r'.\gradlew.bat', 'test'])

    def test_symlinked_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'gradlew'
            target.write_text('')
            target.chmod(0o755)
            try:
                (self.root / 'gradlew').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(gradle_test_command(self.root, {'gradlew'}, 'posix')[0], ['gradle', 'test'])


if __name__ == '__main__':
    unittest.main()
