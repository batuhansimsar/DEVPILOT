"""Julia test discovery must reject linked package lockfiles."""

import tempfile
import unittest
from pathlib import Path

from devpilot.julia_tests import julia_test_command


class JuliaPackageManifestSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Project.toml').touch()
        (self.root / 'test').mkdir()
        (self.root / 'test' / 'runtests.jl').touch()

    def discover(self, *extra_names):
        return julia_test_command(self.root, {'Project.toml', *extra_names})

    def test_regular_package_manifests_are_allowed(self):
        for name in ('Manifest.toml', 'JuliaManifest.toml', 'Manifest-v1.11.toml'):
            (self.root / name).touch()
        self.assertIsNotNone(self.discover('Manifest-v1.11.toml'))

    def test_linked_package_manifests_are_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside.toml'
            target.touch()
            for name in ('Manifest.toml', 'JuliaManifest.toml', 'Manifest-v1.11.toml'):
                with self.subTest(name=name):
                    marker = self.root / name
                    try:
                        marker.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('File symlinks unavailable')
                    self.assertIsNone(self.discover(name))
                    marker.unlink()

    def test_broken_manifest_symlink_is_rejected(self):
        marker = self.root / 'Manifest.toml'
        try:
            marker.symlink_to(self.root / 'missing.toml')
        except (OSError, NotImplementedError):
            self.skipTest('File symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_directory_named_manifest_is_rejected(self):
        marker = self.root / 'JuliaManifest.toml'
        marker.mkdir()
        self.assertIsNone(self.discover())

    def test_unrelated_files_do_not_block_discovery(self):
        (self.root / 'notes.toml').touch()
        self.assertIsNotNone(self.discover('notes.toml'))


if __name__ == '__main__':
    unittest.main()
