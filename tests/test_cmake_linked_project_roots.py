"""CTest discovery must not escape through linked project roots."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cmake_tests import cmake_test_command


class CMakeLinkedProjectRootTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name) / 'project'
        self.root.mkdir()
        (self.root / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.20)\n')
        (self.root / 'build').mkdir()
        (self.root / 'build' / 'CTestTestfile.cmake').write_text('add_test(ok ok)\n')

    def test_regular_root_still_discovers_ctest(self):
        result = cmake_test_command(self.root, {'CMakeLists.txt'})
        self.assertEqual(result['argv'][0], 'ctest')

    def test_linked_project_root_is_rejected(self):
        linked = Path(self.work.name) / 'linked'
        try:
            linked.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(cmake_test_command(linked, {'CMakeLists.txt'}))

    def test_linked_parent_is_rejected(self):
        linked_parent = Path(self.work.name) / 'other'
        try:
            linked_parent.symlink_to(self.root.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(cmake_test_command(linked_parent / 'project', {'CMakeLists.txt'}))

    def test_uninspectable_root_fails_closed(self):
        with patch('devpilot.cmake_tests.ensure_unlinked_scan_path',
                   side_effect=OSError('private')):
            self.assertIsNone(cmake_test_command(self.root, {'CMakeLists.txt'}))


if __name__ == '__main__':
    unittest.main()
