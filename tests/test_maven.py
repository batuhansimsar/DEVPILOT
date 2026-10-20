"""Maven wrapper discovery is read-only and platform-aware."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.maven import maven_test_command


class MavenDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_no_wrapper_falls_back_to_installed_maven(self):
        for platform in ('nt', 'posix'):
            with self.subTest(platform=platform):
                argv, reason = maven_test_command(self.root, set(), platform)
                self.assertEqual(argv, ['mvn', 'test'])
                self.assertIn('no usable wrapper', reason)

    @unittest.skipIf(os.name == 'nt', 'POSIX mode bits not supported on Windows')
    def test_posix_wrapper_must_be_executable(self):
        script = self.root / 'mvnw'
        script.write_text('#!/bin/sh\n')
        script.chmod(0o644)
        self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'posix')[0], ['mvn', 'test'])
        script.chmod(0o755)
        self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'posix')[0], ['./mvnw', 'test'])

    def test_windows_uses_cmd_wrapper_and_not_unix_script(self):
        (self.root / 'mvnw').write_text('unused')
        self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'nt')[0], ['mvn', 'test'])
        (self.root / 'mvnw.cmd').write_text('@echo off\n')
        argv, reason = maven_test_command(self.root, {'mvnw', 'mvnw.cmd'}, 'nt')
        self.assertEqual(argv, [r'.\mvnw.cmd', 'test'])
        self.assertEqual(reason, 'Maven Windows wrapper')

    def test_symlinked_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'mvnw'
            target.write_text('#!/bin/sh\n')
            target.chmod(0o755)
            try:
                (self.root / 'mvnw').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'posix')[0], ['mvn', 'test'])

    def test_missing_and_directory_wrappers_are_rejected(self):
        (self.root / 'mvnw').mkdir()
        self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'posix')[0], ['mvn', 'test'])
        self.assertEqual(maven_test_command(self.root, {'mvnw.cmd'}, 'nt')[0], ['mvn', 'test'])

    def test_discovery_never_executes_wrapper(self):
        (self.root / 'mvnw').write_text('#!/bin/sh\nexit 1\n')
        with patch('devpilot.maven.os.access', return_value=True) as access, \
                patch('os.system', side_effect=AssertionError('must not execute')):
            self.assertEqual(maven_test_command(self.root, {'mvnw'}, 'posix')[0], ['./mvnw', 'test'])
        access.assert_called_once()


if __name__ == '__main__':
    unittest.main()
