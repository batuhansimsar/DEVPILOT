"""Julia test discovery must be explicit, read-only and symlink-safe."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.julia_tests import julia_test_command


class JuliaTestDiscoveryTests(unittest.TestCase):
    def test_project_manifest_proposes_pkg_test_without_executing(self):
        for name in ('Project.toml', 'JuliaProject.toml'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('', encoding='utf-8')
                (root / 'test').mkdir()
                (root / 'test' / 'runtests.jl').write_text('using Test\n', encoding='utf-8')
                with patch('subprocess.run') as run:
                    plan = julia_test_command(root, {name})
                    run.assert_not_called()
                self.assertEqual(plan, {
                    'ecosystem': 'Julia',
                    'argv': ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
                    'reason': 'Julia project with test/runtests.jl',
                })

    def test_manifest_only_is_not_a_testable_julia_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('Manifest.toml', 'JuliaManifest.toml', 'Manifest-v1.11.toml'):
                (root / name).touch()
            self.assertIsNone(julia_test_command(root, {
                'Manifest.toml', 'JuliaManifest.toml', 'Manifest-v1.11.toml'
            }))

    def test_missing_project_file_is_not_trusted_from_names_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))

    def test_symlinked_project_manifest_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            target = Path(elsewhere) / 'Project.toml'
            target.touch()
            try:
                (root / 'Project.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('file symlinks unavailable')
            (root / 'test').mkdir()
            (root / 'test' / 'runtests.jl').touch()
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))


if __name__ == '__main__':
    unittest.main()
