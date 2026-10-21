"""PHPUnit conventional suite discovery must inspect all descendants."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.php_tests import php_test_command


class PHPUnitTreeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        (self.root / 'composer.json').write_text('{}', encoding='utf-8')
        self.tests = self.root / 'tests'
        self.tests.mkdir()

    def discover(self):
        return php_test_command(self.root, {'composer.json'})

    def test_regular_file_without_links_is_discovered(self):
        (self.tests / 'ExampleTest.php').touch()
        self.assertEqual(self.discover()['argv'], ['php', 'vendor/bin/phpunit', 'tests'])

    def test_later_symlinked_file_invalidates_earlier_test(self):
        (self.tests / 'ExampleTest.php').touch()
        try:
            (self.tests / 'LinkedTest.php').symlink_to(self.tests / 'ExampleTest.php')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_nested_symlink_invalidates_earlier_test(self):
        (self.tests / 'ExampleTest.php').touch()
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir()
        try:
            (self.tests / 'linked').symlink_to(elsewhere, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_unreadable_nested_directory_invalidates_earlier_test(self):
        (self.tests / 'ExampleTest.php').touch()
        nested = self.tests / 'Nested'
        nested.mkdir()
        original_iterdir = Path.iterdir

        def patched_iterdir(path):
            if path == nested:
                raise PermissionError('unreadable nested directory')
            return original_iterdir(path)

        with patch.object(Path, 'iterdir', patched_iterdir):
            self.assertIsNone(self.discover())

    def test_tree_without_tests_returns_none(self):
        (self.tests / 'Helper.php').touch()
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
