"""Root unittest discovery cannot import linked modules in nested packages."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.unittest_tree_safety import root_unittest_imports_are_safe


class RootUnittestTreeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'test_root.py').touch()

    def link(self, source, target, *, directory=False):
        try:
            source.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')

    def test_regular_nested_packages_are_allowed(self):
        package = self.root / 'pkg' / 'nested'
        package.mkdir(parents=True)
        (package.parent / '__init__.py').touch()
        (package / '__init__.py').touch()
        (package / 'test_safe.py').touch()
        self.assertTrue(root_unittest_imports_are_safe(self.root))

    def test_linked_test_in_nested_package_is_rejected(self):
        package = self.root / 'pkg'
        package.mkdir()
        (package / '__init__.py').touch()
        outside = self.root / 'outside.py'
        outside.touch()
        self.link(package / 'test_external.py', outside)
        self.assertFalse(root_unittest_imports_are_safe(self.root))

    def test_linked_non_test_module_in_package_is_rejected(self):
        package = self.root / 'pkg'
        package.mkdir()
        (package / '__init__.py').touch()
        self.link(package / 'helpers.py', self.root / 'test_root.py')
        self.assertFalse(root_unittest_imports_are_safe(self.root))

    def test_linked_nested_package_is_rejected(self):
        package = self.root / 'pkg'
        package.mkdir()
        (package / '__init__.py').touch()
        outside = self.root / 'outside'
        outside.mkdir()
        self.link(package / 'linked', outside, directory=True)
        self.assertFalse(root_unittest_imports_are_safe(self.root))

    def test_linked_init_is_rejected(self):
        package = self.root / 'pkg'
        package.mkdir()
        self.link(package / '__init__.py', self.root / 'test_root.py')
        self.assertFalse(root_unittest_imports_are_safe(self.root))

    def test_unimportable_subdirectory_does_not_expand_discovery(self):
        directory = self.root / 'fixtures'
        directory.mkdir()
        self.link(directory / 'fixture.py', self.root / 'test_root.py')
        self.assertTrue(root_unittest_imports_are_safe(self.root))

    def test_directory_entry_limit_fails_closed(self):
        (self.root / 'another.py').touch()
        with patch('devpilot.unittest_tree_safety.MAX_UNITTEST_DISCOVERY_ENTRIES', 1):
            self.assertFalse(root_unittest_imports_are_safe(self.root))

    def test_unreadable_directory_fails_closed(self):
        with patch('pathlib.Path.iterdir', side_effect=OSError('secret location')):
            self.assertFalse(root_unittest_imports_are_safe(self.root))


if __name__ == '__main__':
    unittest.main()
