"""Julia lockfile checks must not trust an incomplete filename inventory."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from devpilot.julia_tests import julia_test_command


class JuliaVersionedManifestInventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'Project.toml').touch()
        (self.root / 'test').mkdir()
        (self.root / 'test' / 'runtests.jl').touch()

    def plan(self):
        return julia_test_command(self.root, {'Project.toml'})

    def test_unlisted_regular_versioned_manifest_allowed(self):
        (self.root / 'Manifest-v1.11.toml').touch()
        self.assertIsNotNone(self.plan())

    def test_unlisted_versioned_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside.toml'
            target.touch()
            try:
                (self.root / 'Manifest-v1.11.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('file symlinks unavailable')
            self.assertIsNone(self.plan())

    def test_unlisted_dangling_versioned_symlink_rejected(self):
        try:
            (self.root / 'Manifest-v2.0.toml').symlink_to(self.root / 'missing.toml')
        except (OSError, NotImplementedError):
            self.skipTest('file symlinks unavailable')
        self.assertIsNone(self.plan())

    def test_unlisted_versioned_directory_rejected(self):
        (self.root / 'Manifest-v1.11.toml').mkdir()
        self.assertIsNone(self.plan())

    def test_root_enumeration_error_fails_closed(self):
        with patch('devpilot.julia_tests.os.scandir', side_effect=PermissionError):
            self.assertIsNone(self.plan())

    def test_oversized_project_root_fails_closed(self):
        for index in range(10_001):
            (self.root / f'file-{index:05d}.txt').touch()
        self.assertIsNone(self.plan())

    def test_unrelated_symlink_does_not_block_discovery(self):
        try:
            (self.root / 'notes.toml').symlink_to(self.root / 'missing.toml')
        except (OSError, NotImplementedError):
            self.skipTest('file symlinks unavailable')
        self.assertIsNotNone(self.plan())
