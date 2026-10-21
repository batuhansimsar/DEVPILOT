"""Versioned Julia manifests omitted by filename scans cannot bypass safety."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.julia_tests import julia_test_command


class UnlistedJuliaVersionedManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'Project.toml').touch()
        (self.root / 'test').mkdir()
        (self.root / 'test' / 'runtests.jl').touch()

    def discover(self):
        return julia_test_command(self.root, {'Project.toml'})

    def test_unlisted_regular_versioned_manifest_is_safe(self):
        (self.root / 'Manifest-v1.11.toml').touch()
        self.assertIsNotNone(self.discover())

    def test_unlisted_versioned_manifest_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'Manifest.toml'
            target.touch()
            try:
                (self.root / 'Manifest-v1.11.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_unlisted_broken_versioned_manifest_symlink_is_rejected(self):
        try:
            (self.root / 'Manifest-v1.11.toml').symlink_to(self.root / 'absent.toml')
        except (OSError, NotImplementedError):
            self.skipTest('File symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_unlisted_versioned_manifest_directory_is_rejected(self):
        (self.root / 'Manifest-v1.11.toml').mkdir()
        self.assertIsNone(self.discover())

    def test_unreadable_root_scan_fails_closed(self):
        with patch('devpilot.julia_tests.os.scandir', side_effect=PermissionError):
            self.assertIsNone(self.discover())

    def test_root_scan_entry_limit(self):
        for index in range(10001):
            (self.root / f'unrelated-{index:04d}.txt').touch()
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
