"""Configured PHPUnit/Pest suites must reject linked or uninspectable test trees."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.php_tests import php_test_command


class ConfiguredPHPSuiteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'composer.json').write_text('{}', encoding='utf-8')
        (self.root / 'phpunit.xml').touch()
        self.names = {'composer.json', 'phpunit.xml'}

    def discover(self):
        return php_test_command(self.root, self.names)

    def test_config_without_conventional_tests_directory_still_supported(self):
        self.assertEqual(self.discover()['argv'],
                         ['php', 'vendor/bin/phpunit', '--configuration', 'phpunit.xml'])

    def test_config_with_regular_test_tree_still_supported(self):
        tests = self.root / 'tests'
        tests.mkdir()
        (tests / 'ExampleTest.php').touch()
        self.assertEqual(self.discover()['argv'][-1], 'phpunit.xml')

    def test_config_with_linked_test_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.root / 'tests').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_config_with_linked_nested_test_file_is_rejected(self):
        nested = self.root / 'tests' / 'Unit'
        nested.mkdir(parents=True)
        (nested / 'SafeTest.php').touch()
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'ExternalTest.php'
            target.touch()
            try:
                (nested / 'ExternalTest.php').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_config_with_unreadable_test_tree_is_rejected(self):
        (self.root / 'tests').mkdir()
        with patch.object(Path, 'iterdir', side_effect=OSError('permission denied')):
            self.assertIsNone(self.discover())

    def test_config_with_oversized_test_tree_is_rejected(self):
        tests = self.root / 'tests'
        tests.mkdir()
        entries = [tests / f'item-{i}' for i in range(4097)]
        with patch.object(Path, 'iterdir', return_value=iter(entries)):
            self.assertIsNone(self.discover())

    def test_pest_config_with_regular_tests_still_uses_pest(self):
        tests = self.root / 'tests'
        tests.mkdir()
        (tests / 'Pest.php').touch()
        (tests / 'FeatureTest.php').touch()
        self.assertEqual(self.discover()['argv'],
                         ['php', 'vendor/bin/pest', '--configuration', 'phpunit.xml'])


if __name__ == '__main__':
    unittest.main()
