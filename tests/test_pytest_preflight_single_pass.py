"""Pytest safety checks do not repeatedly enumerate an untrusted project root."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import _pytest_suites_are_safe


class PytestPreflightTests(unittest.TestCase):
    def test_root_enumerated_only_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            (root / 'tests' / 'test_valid.py').touch()
            original = Path.iterdir
            seen = []

            def tracked_iterdir(path):
                if path == root:
                    seen.append(path)
                return original(path)

            with patch('devpilot.python_tests.Path.iterdir', autospec=True,
                       side_effect=tracked_iterdir):
                self.assertTrue(_pytest_suites_are_safe(root))
            self.assertEqual(len(seen), 1)

    def test_linked_root_pytest_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'tests').mkdir()
            target = Path(outside) / 'pytest.ini'
            target.touch()
            try:
                (root / 'pytest.ini').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertFalse(_pytest_suites_are_safe(root))


if __name__ == '__main__':
    unittest.main()
