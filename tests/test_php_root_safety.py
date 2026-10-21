"""PHP test command discovery must not cross a linked workspace boundary."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.php_tests import php_test_command


class PHPProjectRootSafetyTests(unittest.TestCase):
    def test_symlinked_selected_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            real_root = base / 'external'
            real_root.mkdir()
            (real_root / 'composer.json').write_text('{}', encoding='utf-8')
            (real_root / 'phpunit.xml').touch()
            alias = base / 'alias'
            try:
                alias.symlink_to(real_root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(php_test_command(alias, {'composer.json', 'phpunit.xml'}))

    def test_symlinked_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            real_root = base / 'external' / 'project'
            real_root.mkdir(parents=True)
            (real_root / 'composer.json').write_text('{}', encoding='utf-8')
            (real_root / 'phpunit.xml').touch()
            alias = base / 'alias'
            try:
                alias.symlink_to(real_root.parent, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(php_test_command(alias / 'project', {'composer.json', 'phpunit.xml'}))

    def test_failed_root_check_does_not_inspect_markers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('devpilot.php_tests.ensure_unlinked_scan_path', side_effect=OSError('blocked')):
                with patch.object(Path, 'is_file', side_effect=AssertionError('must not inspect')):
                    self.assertIsNone(php_test_command(root, {'composer.json', 'phpunit.xml'}))

    def test_regular_nested_root_still_discovers_phpunit_and_pest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            root.mkdir()
            (root / 'composer.json').write_text('{}', encoding='utf-8')
            (root / 'phpunit.xml').touch()
            self.assertEqual(
                php_test_command(root, {'composer.json', 'phpunit.xml'})['argv'],
                ['php', 'vendor/bin/phpunit', '--configuration', 'phpunit.xml'],
            )
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'Pest.php').touch()
            self.assertEqual(
                php_test_command(root, {'composer.json', 'phpunit.xml'})['argv'],
                ['php', 'vendor/bin/pest', '--configuration', 'phpunit.xml'],
            )


if __name__ == '__main__':
    unittest.main()
