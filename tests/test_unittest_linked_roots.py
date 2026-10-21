"""The unittest tree preflight rejects linked roots even for direct callers."""

import tempfile
import unittest
from pathlib import Path

from devpilot.unittest_tree_safety import root_unittest_imports_are_safe


class UnittestLinkedRootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        (self.project / 'test_safe.py').touch()

    def link(self, path: Path, target: Path):
        try:
            path.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlinks unavailable')

    def test_direct_directory_is_safe(self):
        self.assertTrue(root_unittest_imports_are_safe(self.project))

    def test_linked_project_root_is_rejected(self):
        alias = self.root / 'alias'
        self.link(alias, self.project)
        self.assertFalse(root_unittest_imports_are_safe(alias))

    def test_linked_project_ancestor_is_rejected(self):
        alias = self.root / 'alias'
        self.link(alias, self.root)
        self.assertFalse(root_unittest_imports_are_safe(alias / 'project'))


if __name__ == '__main__':
    unittest.main()
