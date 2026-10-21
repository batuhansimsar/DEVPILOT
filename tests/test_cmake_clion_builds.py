"""CMake IDE-build discovery regressions and symlink safety."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cmake_tests import cmake_test_command


class CMakeIDEBuildDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('project(example)')

    def configure(self, name):
        folder = self.root / name
        folder.mkdir()
        (folder / 'CTestTestfile.cmake').write_text('add_test(sample sample)')

    def test_debug_build_supported(self):
        self.configure('cmake-build-debug')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'}), {
            'ecosystem': 'C/C++',
            'argv': ['ctest', '--test-dir', 'cmake-build-debug', '--output-on-failure', '--no-tests=error'],
            'reason': 'configured CMake cmake-build-debug/CTestTestfile.cmake',
        })

    def test_release_build_supported(self):
        self.configure('cmake-build-release')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'cmake-build-release')

    def test_prefer_conventional_build_over_ide_builds(self):
        for name in ('build', 'cmake-build-debug', 'cmake-build-release'):
            self.configure(name)
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_prefer_debug_over_release(self):
        for name in ('cmake-build-release', 'cmake-build-debug'):
            self.configure(name)
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'cmake-build-debug')

    def test_requires_ctest_description(self):
        (self.root / 'cmake-build-debug').mkdir()
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_missing_source_manifest_not_detected(self):
        self.configure('cmake-build-debug')
        self.assertIsNone(cmake_test_command(self.root, set()))

    def test_linked_ide_build_directory_is_skipped(self):
        with tempfile.TemporaryDirectory() as external:
            (Path(external) / 'CTestTestfile.cmake').touch()
            try:
                (self.root / 'cmake-build-debug').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_linked_ctest_description_is_skipped(self):
        with tempfile.TemporaryDirectory() as external:
            external_ctest = Path(external) / 'CTestTestfile.cmake'
            external_ctest.touch()
            folder = self.root / 'cmake-build-debug'
            folder.mkdir()
            try:
                (folder / 'CTestTestfile.cmake').symlink_to(external_ctest)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_falls_back_when_first_build_is_unconfigured(self):
        (self.root / 'build').mkdir()
        self.configure('cmake-build-debug')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'cmake-build-debug')


if __name__ == '__main__':
    unittest.main()
