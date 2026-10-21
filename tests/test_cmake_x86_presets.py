"""Recognize configured Visual Studio x86 CMake presets without traversing links."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cmake_tests import cmake_test_command


_X86_PRESETS = (
    'out/build/x86-Debug',
    'out/build/x86-Release',
    'out/build/x86-RelWithDebInfo',
    'out/build/x86-MinSizeRel',
)


class CMakeX86PresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('enable_testing()\n')

    def configure(self, name):
        build = self.root / name
        build.mkdir(parents=True, exist_ok=True)
        (build / 'CTestTestfile.cmake').write_text('add_test(example example)\n')
        return build

    def test_all_four_x86_preset_variants(self):
        for name in _X86_PRESETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'CMakeLists.txt').touch()
                build = root / name
                build.mkdir(parents=True)
                (build / 'CTestTestfile.cmake').touch()
                self.assertEqual(cmake_test_command(root, {'CMakeLists.txt'}), {
                    'ecosystem': 'C/C++',
                    'argv': ['ctest', '--test-dir', name, '--output-on-failure', '--no-tests=error'],
                    'reason': f'configured CMake {name}/CTestTestfile.cmake',
                })

    def test_unconfigured_x86_preset_is_ignored(self):
        (self.root / _X86_PRESETS[0]).mkdir(parents=True)
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_root_build_precedes_x86_preset(self):
        self.configure(_X86_PRESETS[0])
        self.configure('build')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_linked_x86_build_ancestor_is_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'x86-Debug'
            external.mkdir()
            (external / 'CTestTestfile.cmake').touch()
            (self.root / 'out').mkdir()
            try:
                (self.root / 'out/build').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_linked_ctest_file_is_not_followed(self):
        build = self.root / _X86_PRESETS[0]
        build.mkdir(parents=True)
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'CTestTestfile.cmake'
            external.touch()
            try:
                (build / 'CTestTestfile.cmake').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
