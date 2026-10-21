"""Julia test discovery must be opt-in to execution and avoid linked test files."""

import tempfile
import unittest
from pathlib import Path

from devpilot.julia_tests import julia_test_command


class JuliaTestDiscoveryTests(unittest.TestCase):
    def test_project_with_standard_tests_produces_pkg_test_command(self):
        for manifest in ('Project.toml', 'JuliaProject.toml'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / manifest).touch()
                (root / 'test').mkdir()
                (root / 'test' / 'runtests.jl').write_text('using Test\n', encoding='utf-8')
                self.assertEqual(julia_test_command(root, {manifest}), {
                    'ecosystem': 'Julia',
                    'argv': ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
                    'reason': 'Julia project with test/runtests.jl',
                })

    def test_lockfiles_or_missing_test_entry_are_not_runnable_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            for names in (set(), {'Manifest.toml'}, {'JuliaManifest.toml'},
                          {'Manifest-v1.11.toml'}):
                with self.subTest(names=names):
                    self.assertIsNone(julia_test_command(root, names))
            (root / 'test' / 'runtests.jl').unlink()
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))

    def test_symlinked_test_directory_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / 'external'
            external.mkdir()
            (external / 'runtests.jl').touch()
            try:
                (root / 'test').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks not available')
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))

    def test_symlinked_test_entry_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            target = root / 'outside.jl'
            target.touch()
            try:
                (root / 'test' / 'runtests.jl').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks not available')
            self.assertIsNone(julia_test_command(root, {'JuliaProject.toml'}))


if __name__ == '__main__':
    unittest.main()
