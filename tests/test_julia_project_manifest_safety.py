"""Reject linked or non-file Julia project manifests during test discovery."""

import tempfile
import unittest
from pathlib import Path

from devpilot.julia_tests import julia_test_command


class JuliaProjectManifestSafetyTests(unittest.TestCase):
    def make_tests(self, root: Path):
        (root / 'test').mkdir()
        (root / 'test' / 'runtests.jl').touch()

    def test_regular_project_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Project.toml').touch()
            self.make_tests(root)
            self.assertEqual(julia_test_command(root, {'Project.toml'})['ecosystem'], 'Julia')

    def test_symlinked_project_manifest_does_not_enable_tests(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            outside = Path(external) / 'external.toml'
            outside.write_text('name = "outside"', encoding='utf-8')
            try:
                (root / 'Project.toml').symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.make_tests(root)
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))

    def test_linked_priority_marker_rejected_with_real_alternative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'JuliaProject.toml').touch()
            try:
                (root / 'Project.toml').symlink_to(root / 'JuliaProject.toml')
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks not supported')
            self.make_tests(root)
            self.assertIsNone(julia_test_command(root, {'Project.toml', 'JuliaProject.toml'}))

    def test_directory_named_project_manifest_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Project.toml').mkdir()
            self.make_tests(root)
            self.assertIsNone(julia_test_command(root, {'Project.toml'}))


if __name__ == '__main__':
    unittest.main()
