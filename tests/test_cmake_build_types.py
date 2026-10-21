"""CTest previews cover standard optimized CLion configurations safely."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cmake_tests import cmake_test_command


class CMakeAdditionalBuildTypesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('project(example)')

    def configure(self, name):
        build = self.root / name
        build.mkdir()
        (build / 'CTestTestfile.cmake').write_text('add_test(sample sample)')

    def test_optimized_clion_builds_are_supported(self):
        for name in ('cmake-build-relwithdebinfo', 'cmake-build-minsizerel'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'CMakeLists.txt').write_text('project(example)')
                build = root / name
                build.mkdir()
                (build / 'CTestTestfile.cmake').touch()
                self.assertEqual(cmake_test_command(root, {'CMakeLists.txt'}), {
                    'ecosystem': 'C/C++',
                    'argv': ['ctest', '--test-dir', name, '--output-on-failure', '--no-tests=error'],
                    'reason': f'configured CMake {name}/CTestTestfile.cmake',
                })

    def test_existing_configurations_take_priority(self):
        for name in ('cmake-build-minsizerel', 'cmake-build-relwithdebinfo',
                     'cmake-build-release', 'cmake-build-debug', 'build'):
            self.configure(name)
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_optimized_build_directory_symlinks_are_skipped(self):
        with tempfile.TemporaryDirectory() as external:
            (Path(external) / 'CTestTestfile.cmake').touch()
            try:
                (self.root / 'cmake-build-relwithdebinfo').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.configure('cmake-build-minsizerel')
            self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2],
                             'cmake-build-minsizerel')

    def test_optimized_build_marker_symlink_is_skipped(self):
        with tempfile.TemporaryDirectory() as external:
            source = Path(external) / 'CTestTestfile.cmake'
            source.touch()
            build = self.root / 'cmake-build-relwithdebinfo'
            build.mkdir()
            try:
                (build / 'CTestTestfile.cmake').symlink_to(source)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_unconfigured_optimized_build_is_not_runnable(self):
        (self.root / 'cmake-build-minsizerel').mkdir()
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
