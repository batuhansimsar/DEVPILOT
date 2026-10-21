"""Regression tests for Pest-aware Composer test command discovery."""

import tempfile
import unittest
from pathlib import Path

from devpilot.php_tests import php_test_command


class PestDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'composer.json').write_text('{}', encoding='utf-8')
        self.tests = self.root / 'tests'
        self.tests.mkdir()

    def discover(self, extra=()):
        return php_test_command(self.root, {'composer.json', *extra})

    def test_pest_marker_selects_pest_with_nested_tests(self):
        (self.tests / 'Pest.php').touch()
        unit = self.tests / 'Unit'
        unit.mkdir()
        (unit / 'FeatureTest.php').touch()
        result = self.discover()
        self.assertEqual(result['argv'], ['php', 'vendor/bin/pest', 'tests'])
        self.assertIn('Pest', result['reason'])

    def test_pest_marker_with_phpunit_xml_preserves_configuration(self):
        (self.tests / 'Pest.php').touch()
        (self.root / 'phpunit.xml').touch()
        result = self.discover({'phpunit.xml'})
        self.assertEqual(result['argv'], ['php', 'vendor/bin/pest', '--configuration', 'phpunit.xml'])

    def test_pest_marker_alone_is_not_an_executable_suite(self):
        (self.tests / 'Pest.php').touch()
        self.assertIsNone(self.discover())

    def test_linked_pest_marker_does_not_select_pest(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'Pest.php'
            target.touch()
            try:
                (self.tests / 'Pest.php').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            (self.tests / 'ExampleTest.php').touch()
            self.assertIsNone(self.discover())

    def test_linked_test_directory_does_not_enable_pest(self):
        self.tests.rmdir()
        with tempfile.TemporaryDirectory() as external:
            target = Path(external)
            (target / 'Pest.php').touch()
            (target / 'ExampleTest.php').touch()
            try:
                self.tests.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_regular_phpunit_suite_keeps_existing_command(self):
        (self.tests / 'ExampleTest.php').touch()
        self.assertEqual(self.discover()['argv'], ['php', 'vendor/bin/phpunit', 'tests'])


if __name__ == '__main__':
    unittest.main()
