"""A symlinked scan root must not bypass os.walk(followlinks=False)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import walk_project


class WalkRootSymlinkTests(unittest.TestCase):
    def test_symlinked_root_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'private.txt').write_text('secret', encoding='utf-8')
            link = base / 'project'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks are unavailable')
            problems = []
            with patch('devpilot.walk.os.walk', side_effect=AssertionError('must not scan outside root')):
                self.assertEqual(list(walk_project(link, problems)), [])
            self.assertEqual(problems, ['Cannot inspect .: project root is a symbolic link'])
            self.assertNotIn('private.txt', str(problems))

    def test_regular_directory_remains_scannable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'visible.txt').touch()
            problems = []
            entries = list(walk_project(root, problems))
            self.assertEqual(entries[0][2], ['visible.txt'])
            self.assertEqual(problems, [])

    def test_dangling_symlink_is_reported_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'project'
            try:
                link.symlink_to(Path(temporary) / 'missing', target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks are unavailable')
            problems = []
            self.assertEqual(list(walk_project(link, problems)), [])
            self.assertEqual(problems, ['Cannot inspect .: project root is a symbolic link'])


if __name__ == '__main__':
    unittest.main()
