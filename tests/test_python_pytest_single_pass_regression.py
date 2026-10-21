"""Avoid redundant root scans while checking all pytest entry points."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import _pytest_suites_are_safe


class PytestRootScanTests(unittest.TestCase):
    def test_root_is_listed_once_for_unlinked_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_one.py').touch()
            original = Path.iterdir
            visited = []

            def recording_iterdir(path):
                visited.append(path)
                return original(path)

            with patch.object(Path, 'iterdir', autospec=True, side_effect=recording_iterdir):
                self.assertTrue(_pytest_suites_are_safe(root))
            self.assertEqual(visited.count(root), 1)

    def test_root_linked_test_directory_and_config_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'tests').mkdir()
            target = Path(external)
            for name, is_directory in (('pytest.ini', False), ('test_external', True),
                                       ('testing.py', False), ('pyproject.toml', False)):
                with self.subTest(name=name):
                    link = root / name
                    destination = target if is_directory else target / 'outside'
                    if not is_directory:
                        destination.touch()
                    try:
                        link.symlink_to(destination, target_is_directory=is_directory)
                    except (OSError, NotImplementedError):
                        self.skipTest('Symlinks unavailable')
                    self.assertFalse(_pytest_suites_are_safe(root))
                    link.unlink()

    def test_unrelated_link_does_not_block_suite(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'tests').mkdir()
            try:
                (root / 'assets').symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertTrue(_pytest_suites_are_safe(root))


if __name__ == '__main__':
    unittest.main()
