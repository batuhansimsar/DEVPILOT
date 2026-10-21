"""An omitted higher-priority Julia project marker must not escape the root."""
import tempfile
import unittest
from pathlib import Path
from devpilot.julia_tests import julia_test_command


class UnlistedJuliaProjectManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'JuliaProject.toml').touch()
        (self.root / 'test').mkdir()
        (self.root / 'test' / 'runtests.jl').touch()

    def test_regular_fallback_project_is_allowed(self):
        self.assertIsNotNone(julia_test_command(self.root, {'JuliaProject.toml'}))

    def test_unlisted_priority_project_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'Project.toml'
            target.touch()
            try:
                (self.root / 'Project.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(julia_test_command(self.root, {'JuliaProject.toml'}))

    def test_unlisted_broken_project_symlink_is_rejected(self):
        try:
            (self.root / 'Project.toml').symlink_to(self.root / 'absent.toml')
        except (OSError, NotImplementedError):
            self.skipTest('File symlinks unavailable')
        self.assertIsNone(julia_test_command(self.root, {'JuliaProject.toml'}))

    def test_unlisted_priority_project_directory_is_rejected(self):
        (self.root / 'Project.toml').mkdir()
        self.assertIsNone(julia_test_command(self.root, {'JuliaProject.toml'}))


if __name__ == '__main__':
    unittest.main()
