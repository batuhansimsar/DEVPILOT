"""CTest can find safe, known nested CMake preset build directories."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cmake_tests import cmake_test_command


class CMakePresetBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('enable_testing()\n')

    def configured(self, name):
        folder = self.root / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'CTestTestfile.cmake').write_text('add_test(demo demo)\n')
        return folder

    def test_discovers_common_preset_build_directories(self):
        for name in ('out/build', 'out/build/default', 'out/build/debug',
                     'out/build/release', 'out/build/x64-Debug', 'out/build/x64-Release'):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as scratch:
                    root = Path(scratch)
                    (root / 'CMakeLists.txt').touch()
                    build = root / name
                    build.mkdir(parents=True)
                    (build / 'CTestTestfile.cmake').touch()
                    self.assertEqual(cmake_test_command(root, {'CMakeLists.txt'}), {
                        'ecosystem': 'C/C++',
                        'argv': ['ctest', '--test-dir', name, '--output-on-failure', '--no-tests=error'],
                        'reason': f'configured CMake {name}/CTestTestfile.cmake',
                    })

    def test_root_build_directory_takes_precedence(self):
        self.configured('out/build/default')
        self.configured('build')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_does_not_accept_nested_symlink_ancestors(self):
        with tempfile.TemporaryDirectory() as outside:
            foreign = Path(outside) / 'build' / 'default'
            foreign.mkdir(parents=True)
            (foreign / 'CTestTestfile.cmake').touch()
            for link_name, target in (('out', Path(outside)), ('out/build', Path(outside) / 'build')):
                with self.subTest(link=link_name):
                    out = self.root / 'out'
                    if out.is_symlink():
                        out.unlink()
                    elif out.is_dir():
                        (out / 'build').unlink()
                        out.rmdir()
                    link = self.root / link_name
                    link.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        link.symlink_to(target, target_is_directory=True)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_rejects_linked_marker_even_in_nested_build(self):
        folder = self.configured('out/build/default')
        marker = folder / 'CTestTestfile.cmake'
        marker.unlink()
        other = self.root / 'foreign.cmake'
        other.touch()
        try:
            marker.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_only_configured_fixed_directories_are_accepted(self):
        self.configured('out/build/unknown-custom-profile')
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_discovery_does_not_execute_ctest(self):
        self.configured('out/build/default')
        with patch('subprocess.run', side_effect=AssertionError('must be read-only')):
            self.assertIsNotNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
