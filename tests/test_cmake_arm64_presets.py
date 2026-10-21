"""ARM64 CMake presets are discovered without following linked paths."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cmake_tests import cmake_test_command


ARM64_PRESETS = (
    'out/build/arm64-Debug',
    'out/build/arm64-Release',
    'out/build/arm64-RelWithDebInfo',
    'out/build/arm64-MinSizeRel',
)


class CMakeArm64PresetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('enable_testing()\n')

    def configure(self, relative):
        directory = self.root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'CTestTestfile.cmake').write_text('add_test(example example)\n')
        return directory

    def test_discovers_each_configured_arm64_preset(self):
        for name in ARM64_PRESETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as workspace:
                root = Path(workspace)
                (root / 'CMakeLists.txt').touch()
                build = root / name
                build.mkdir(parents=True)
                (build / 'CTestTestfile.cmake').touch()
                self.assertEqual(cmake_test_command(root, {'CMakeLists.txt'}), {
                    'ecosystem': 'C/C++',
                    'argv': ['ctest', '--test-dir', name, '--output-on-failure', '--no-tests=error'],
                    'reason': f'configured CMake {name}/CTestTestfile.cmake',
                })

    def test_ignores_unconfigured_or_unknown_preset(self):
        (self.root / ARM64_PRESETS[0]).mkdir(parents=True)
        self.configure('out/build/arm64-Custom')
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_root_build_directory_takes_priority(self):
        self.configure(ARM64_PRESETS[0])
        self.configure('build')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_rejects_symlinked_build_ancestor(self):
        with tempfile.TemporaryDirectory() as outside:
            foreign = Path(outside) / 'arm64-Debug'
            foreign.mkdir()
            (foreign / 'CTestTestfile.cmake').touch()
            (self.root / 'out').mkdir()
            try:
                (self.root / 'out/build').symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_rejects_symlinked_ctest_file(self):
        build = self.root / ARM64_PRESETS[0]
        build.mkdir(parents=True)
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'CTestTestfile.cmake'
            target.touch()
            try:
                (build / 'CTestTestfile.cmake').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
