"""Configured optimized CMake presets are discoverable without unsafe traversal."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cmake_tests import cmake_test_command


_OPTIMIZED_PRESETS = (
    'out/build/relwithdebinfo',
    'out/build/minsizerel',
    'out/build/x64-RelWithDebInfo',
    'out/build/x64-MinSizeRel',
)


class OptimizedCMakePresetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'CMakeLists.txt').write_text('enable_testing()\n')

    def configured(self, name):
        build = self.root / name
        build.mkdir(parents=True, exist_ok=True)
        (build / 'CTestTestfile.cmake').write_text('add_test(example example)\n')
        return build

    def test_finds_configured_optimized_presets(self):
        for name in _OPTIMIZED_PRESETS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'CMakeLists.txt').touch()
                build = root / name
                build.mkdir(parents=True)
                (build / 'CTestTestfile.cmake').touch()
                self.assertEqual(cmake_test_command(root, {'CMakeLists.txt'}), {
                    'ecosystem': 'C/C++',
                    'argv': ['ctest', '--test-dir', name, '--output-on-failure', '--no-tests=error'],
                    'reason': f'configured CMake {name}/CTestTestfile.cmake',
                })

    def test_unconfigured_optimized_preset_is_ignored(self):
        (self.root / 'out/build/x64-RelWithDebInfo').mkdir(parents=True)
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_existing_build_precedes_optimized_preset(self):
        self.configured('out/build/x64-MinSizeRel')
        self.configured('build')
        self.assertEqual(cmake_test_command(self.root, {'CMakeLists.txt'})['argv'][2], 'build')

    def test_linked_preset_ancestors_are_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / 'x64-RelWithDebInfo'
            outside.mkdir()
            (outside / 'CTestTestfile.cmake').touch()
            (self.root / 'out').mkdir()
            try:
                (self.root / 'out/build').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))

    def test_linked_preset_marker_is_rejected(self):
        build = self.root / 'out/build/x64-MinSizeRel'
        build.mkdir(parents=True)
        source = self.root / 'CTestTestfile.cmake'
        source.touch()
        try:
            (build / 'CTestTestfile.cmake').symlink_to(source)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
