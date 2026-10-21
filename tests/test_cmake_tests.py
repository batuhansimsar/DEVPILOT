"""CTest discovery runs no project code and rejects unconfigured trees."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cmake_tests import cmake_test_command
from devpilot.core import detect_projects, doctor_report, test_commands
from devpilot.cli import main


class CMakeTestDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\n')

    def configure(self):
        (self.root / 'build').mkdir()
        (self.root / 'build' / 'CTestTestfile.cmake').write_text('add_test(sample sample)\n')

    def test_detects_configured_build_and_filters_cpp(self):
        self.configure()
        cmd = cmake_test_command(self.root, {'CMakeLists.txt'})
        self.assertEqual(cmd, {
            'ecosystem': 'C/C++',
            'argv': ['ctest', '--test-dir', 'build', '--output-on-failure', '--no-tests=error'],
            'reason': 'configured CMake build/CTestTestfile.cmake',
        })
        self.assertEqual(test_commands(self.root), [cmd])
        self.assertEqual(detect_projects(self.root), ['C/C++'])

    def test_requires_configured_build_and_regular_markers(self):
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))
        self.configure()
        self.assertIsNone(cmake_test_command(self.root, set()))
        (self.root / 'build' / 'CTestTestfile.cmake').unlink()
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_rejects_symlinked_source_manifest_or_test_description(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'external'
            outside.write_text('')
            self.configure()
            source = self.root / 'CMakeLists.txt'
            source.unlink()
            try:
                source.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))
            source.unlink()
            source.touch()
            ctest = self.root / 'build' / 'CTestTestfile.cmake'
            ctest.unlink()
            ctest.symlink_to(outside)
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_rejects_linked_build_directory(self):
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / 'CTestTestfile.cmake').touch()
            try:
                (self.root / 'build').symlink_to(other, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_doctor_checks_ctest(self):
        with patch('devpilot.core.shutil.which', return_value=None):
            report = doctor_report(self.root)
        self.assertIn('Missing ctest required by detected project', report['warnings'])

    def test_cli_requires_yes_before_running(self):
        self.configure()
        with patch('devpilot.cli.command_result') as runner:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['test', '--path', str(self.root), '--ecosystem', 'cpp', '--json'])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.getvalue())['executed'])
            runner.assert_not_called()
        with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as runner:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['test', '--path', str(self.root), '--ecosystem', 'cpp', '--yes', '--json'])
            self.assertEqual(code, 0)
            runner.assert_called_once_with(
                ['ctest', '--test-dir', 'build', '--output-on-failure', '--no-tests=error'],
                self.root.resolve(), 120,
            )


if __name__ == '__main__':
    unittest.main()
