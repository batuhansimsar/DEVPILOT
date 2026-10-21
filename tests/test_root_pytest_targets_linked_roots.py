"""Root-level pytest discovery never follows linked workspace paths."""

import tempfile
import unittest
from pathlib import Path

from devpilot.python_test_targets import root_pytest_targets


class RootPytestTargetsLinkedRootsTests(unittest.TestCase):
    def test_regular_root_discovers_only_root_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_local.py').write_text('')
            (root / 'example.py').write_text('')
            self.assertEqual(root_pytest_targets(root, 10), ['./test_local.py'])

    def test_symlinked_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'real'
            root.mkdir()
            (root / 'test_external.py').write_text('')
            linked = Path(directory) / 'linked'
            try:
                linked.symlink_to(root, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks unavailable')
            self.assertIsNone(root_pytest_targets(linked, 10))

    def test_symlinked_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'real'
            nested = real / 'project'
            nested.mkdir(parents=True)
            (nested / 'test_external.py').write_text('')
            alias = Path(directory) / 'alias'
            try:
                alias.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks unavailable')
            self.assertIsNone(root_pytest_targets(alias / 'project', 10))


if __name__ == '__main__':
    unittest.main()
