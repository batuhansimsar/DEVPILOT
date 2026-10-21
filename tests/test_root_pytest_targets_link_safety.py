"""Root pytest discovery must not escape a workspace via linked root paths."""

import tempfile
import unittest
from pathlib import Path

from devpilot.python_test_targets import root_pytest_targets


class RootPytestTargetsLinkSafetyTests(unittest.TestCase):
    def test_direct_linked_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / 'real'
            target.mkdir()
            (target / 'test_real.py').touch()
            alias = base / 'alias'
            try:
                alias.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(root_pytest_targets(alias, 10))

    def test_linked_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / 'outside'
            nested = outside / 'project'
            nested.mkdir(parents=True)
            (nested / 'test_real.py').touch()
            alias = base / 'alias'
            try:
                alias.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(root_pytest_targets(alias / 'project', 10))

    def test_unlinked_root_is_still_discoverable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'test_ok.py').touch()
            self.assertEqual(root_pytest_targets(root, 10), ['./test_ok.py'])


if __name__ == '__main__':
    unittest.main()
