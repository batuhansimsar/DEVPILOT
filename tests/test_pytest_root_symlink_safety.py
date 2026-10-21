"""Pytest plans must not execute linked root-level modules or configuration."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PytestRootLinkTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'test_safe.py').touch()

    def select(self):
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
            return python_test_command(self.root)

    def test_normal_project_remains_supported(self):
        (self.root / 'conftest.py').touch()
        self.assertEqual(self.select()['argv'][-3:], ['-m', 'pytest', 'tests'])

    def test_linked_root_conftest_and_config_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'external'
            target.touch()
            for name in ('conftest.py', 'pytest.ini', 'tox.ini', 'setup.cfg', 'pyproject.toml',
                         'pytest.toml', '.pytest.toml'):
                with self.subTest(name=name):
                    link = self.root / name
                    try:
                        link.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    self.assertIsNone(self.select())
                    link.unlink()

    def test_linked_root_test_modules_are_rejected(self):
        (self.root / 'test_regular.py').touch()
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'external.py'
            target.touch()
            for name in ('test_external.py', 'external_test.py'):
                with self.subTest(name=name):
                    link = self.root / name
                    try:
                        link.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    self.assertIsNone(self.select())
                    link.unlink()

    def test_bounded_root_listing_fails_closed(self):
        (self.root / 'README.md').touch()
        with patch('devpilot.python_tests._MAX_TEST_DISCOVERY_ENTRIES', 1):
            self.assertIsNone(self.select())


if __name__ == '__main__':
    unittest.main()
