"""PHP test discovery rejects non-regular suite entries without running them."""

import os
import tempfile
import unittest
from pathlib import Path

from devpilot.php_tests import php_test_command


@unittest.skipUnless(hasattr(os, 'mkfifo'), 'named pipes are unavailable')
class PHPSpecialNodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'composer.json').write_text('{}', encoding='utf-8')
        self.tests = self.root / 'tests'
        self.tests.mkdir()
        (self.tests / 'SafeTest.php').touch()

    def test_fifo_prevents_conventional_suite_selection(self):
        os.mkfifo(self.tests / 'blocking.fifo')
        self.assertIsNone(php_test_command(self.root, {'composer.json'}))

    def test_nested_fifo_prevents_configured_suite_selection(self):
        (self.root / 'phpunit.xml').touch()
        nested = self.tests / 'Fixtures'
        nested.mkdir()
        os.mkfifo(nested / 'blocking.fifo')
        self.assertIsNone(php_test_command(self.root, {'composer.json', 'phpunit.xml'}))

    def test_regular_suite_still_selectable(self):
        self.assertEqual(php_test_command(self.root, {'composer.json'})['argv'],
                         ['php', 'vendor/bin/phpunit', 'tests'])


if __name__ == '__main__':
    unittest.main()
