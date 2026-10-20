"""Windows Maven test discovery supports safe .bat wrapper fallbacks."""

import tempfile
import unittest
from pathlib import Path

from devpilot.maven import maven_test_command


class MavenBatWrapperTests(unittest.TestCase):
    def test_batch_wrapper_is_discovered(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'MVNW.BAT').write_text('@echo off\n', encoding='utf-8')
            self.assertEqual(maven_test_command(root, {'MVNW.BAT'}, 'nt'),
                             ([r'.\MVNW.BAT', 'test'], 'Maven Windows wrapper'))

    def test_cmd_takes_precedence_over_bat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('mvnw.cmd', 'mvnw.bat'):
                (root / name).write_text('@echo off\n', encoding='utf-8')
            self.assertEqual(maven_test_command(root, {'mvnw.cmd', 'mvnw.bat'}, 'nt')[0],
                             [r'.\mvnw.cmd', 'test'])

    def test_missing_backup_and_directory_are_not_wrappers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mvnw.bat.bak').write_text('backup', encoding='utf-8')
            (root / 'mvnw.bat').mkdir()
            self.assertEqual(maven_test_command(root, {'mvnw.bat.bak', 'mvnw.bat'}, 'nt')[0],
                             ['mvn', 'test'])

    def test_batch_wrapper_is_not_selected_for_posix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'mvnw.bat').write_text('echo hello', encoding='utf-8')
            self.assertEqual(maven_test_command(root, {'mvnw.bat'}, 'posix')[0],
                             ['mvn', 'test'])

    def test_symlinked_batch_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            target = Path(outside) / 'mvnw.bat'
            target.write_text('@echo off\n', encoding='utf-8')
            try:
                (root / 'mvnw.bat').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(maven_test_command(root, {'mvnw.bat'}, 'nt')[0],
                             ['mvn', 'test'])


if __name__ == '__main__':
    unittest.main()
