"""Regression tests for case-insensitive Maven wrapper discovery on Windows."""

import tempfile
import unittest
from pathlib import Path

from devpilot.maven import maven_test_command


class MavenWindowsWrapperCaseTests(unittest.TestCase):
    def test_uppercase_windows_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'MVNW.CMD').write_text('@echo off\n')
            cmd, reason = maven_test_command(root, {'MVNW.CMD'}, 'nt')
            self.assertEqual(cmd, [r'.\MVNW.CMD', 'test'])
            self.assertEqual(reason, 'Maven Windows wrapper')

    def test_mixed_case_windows_wrapper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'MvNw.CmD').write_text('@echo off\n')
            self.assertEqual(maven_test_command(root, {'MvNw.CmD'}, 'nt')[0],
                             [r'.\MvNw.CmD', 'test'])

    def test_nonwrapper_file_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'MVNW.CMD.backup').write_text('')
            self.assertEqual(maven_test_command(root, {'MVNW.CMD.backup'}, 'nt')[0],
                             ['mvn', 'test'])

    def test_linked_uppercase_wrapper_is_not_selected(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            target = Path(outside) / 'wrapper.cmd'
            target.write_text('')
            try:
                (root / 'MVNW.CMD').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(maven_test_command(root, {'MVNW.CMD'}, 'nt')[0],
                             ['mvn', 'test'])


if __name__ == '__main__':
    unittest.main()
