"""Regression coverage for C/C++ workspace discovery."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class CPPWorkspaceDiscoveryTests(unittest.TestCase):
    def test_cmake_and_meson_in_nested_monorepo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'native' / 'cmake').mkdir(parents=True)
            (root / 'native' / 'meson').mkdir(parents=True)
            (root / 'native' / 'cmake' / 'CMakeLists.txt').write_text('project(example)')
            (root / 'native' / 'meson' / 'meson.build').write_text("project('example', 'cpp')")
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 2)
            self.assertEqual([(w['path'], w['ecosystems']) for w in report['workspaces']],
                             [('native/cmake', ['C/C++']), ('native/meson', ['C/C++'])])

    def test_mixed_build_files_count_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('CMakeLists.txt', 'CMakePresets.json', 'meson.build'):
                (root / name).write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            workspace = report['workspaces'][0]
            self.assertEqual(workspace['ecosystems'], ['C/C++'])
            self.assertEqual([m['file'] for m in workspace['manifests']],
                             ['CMakeLists.txt', 'CMakePresets.json', 'meson.build'])

    def test_symlinked_cmake_manifest_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = Path(tmp)
            target = Path(other) / 'CMakeLists.txt'
            target.write_text('project(external)')
            try:
                (root / 'CMakeLists.txt').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks not available')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_skips_generated_cmake_build_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'build').mkdir()
            (root / 'build' / 'CMakeLists.txt').write_text('')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
