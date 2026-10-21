"""Do not follow linked hidden pytest configuration or cache paths."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PytestRootLinkTests(unittest.TestCase):
    def test_root_pytest_hook_config_and_cache_links_rejected(self):
        for name, is_directory in (
            ('.pytest.ini', False),
            ('.pytest_cache', True),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
                root = Path(directory)
                (root / 'tests').mkdir()
                (root / 'tests' / 'test_valid.py').touch()
                target = Path(external) / name
                if is_directory:
                    target.mkdir()
                else:
                    target.touch()
                try:
                    (root / name).symlink_to(target, target_is_directory=is_directory)
                except (OSError, NotImplementedError):
                    self.skipTest('symlinks unavailable')
                with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                    command = python_test_command(root)
                    self.assertTrue(command is None or 'pytest' not in command['argv'])

    def test_regular_configuration_and_hook_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_valid.py').touch()
            (root / '.pytest.ini').touch()
            (root / '.pytest_cache').mkdir()
            with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
                self.assertIn('pytest', python_test_command(root)['argv'])


if __name__ == '__main__':
    unittest.main()
