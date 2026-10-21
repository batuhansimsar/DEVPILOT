"""Pytest discovery must not traverse external linked test trees."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PytestSymlinkSafetyTests(unittest.TestCase):
    def test_nested_file_and_directory_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            nested = root / 'tests' / 'nested'
            nested.mkdir(parents=True)
            (nested / 'test_valid.py').touch()
            target_file = Path(elsewhere) / 'test_outside.py'
            target_file.touch()
            target_dir = Path(elsewhere) / 'other'
            target_dir.mkdir()
            for target, name, is_dir in (
                (target_file, 'test_external.py', False),
                (target_dir, 'test_linked_suite', True),
            ):
                with self.subTest(name=name):
                    link = nested / name
                    try:
                        link.symlink_to(target, target_is_directory=is_dir)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                        self.assertIsNone(python_test_command(root))
                    link.unlink()

    def test_linked_singular_suite_is_rejected_when_plural_exists(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as elsewhere:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_valid.py').touch()
            try:
                (root / 'test').symlink_to(elsewhere, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIsNone(python_test_command(root))

    def test_unreadable_test_tree_does_not_offer_pytest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                with patch.object(Path, 'iterdir', side_effect=OSError('private path')):
                    self.assertIsNone(python_test_command(root))

    def test_excessively_large_tree_is_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'tests'
            suite.mkdir()
            for name in ('test_a.py', 'test_b.py', 'test_c.py'):
                (suite / name).touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                with patch('devpilot.python_tests._MAX_TEST_DISCOVERY_ENTRIES', 2):
                    self.assertIsNone(python_test_command(root))

    def test_regular_suite_still_offers_pytest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'tests' / 'unit'
            nested.mkdir(parents=True)
            (nested / 'test_ok.py').touch()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertEqual(python_test_command(root)['argv'][-2:], ['-m', 'pytest'])


if __name__ == '__main__':
    unittest.main()
