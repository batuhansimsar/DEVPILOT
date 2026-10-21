"""Protect scans when a parent component of the requested root is a symlink."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import walk_project


class WalkAncestorSymlinkTests(unittest.TestCase):
    def test_symlinked_parent_of_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / 'outside'
            nested = outside / 'source'
            nested.mkdir(parents=True)
            (nested / 'private.txt').write_text('secret', encoding='utf-8')
            alias = base / 'project-link'
            try:
                alias.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks are unavailable')

            problems = []
            with patch('devpilot.walk.os.walk', side_effect=AssertionError('must not scan through symlink')):
                self.assertEqual(list(walk_project(alias / 'source', problems)), [])
            self.assertEqual(problems, ['Cannot inspect .: project path contains a symbolic link'])
            self.assertNotIn('private.txt', str(problems))
            self.assertNotIn(str(outside), str(problems))

    def test_filesystem_root_alias_does_not_block_scanning(self):
        # Some operating systems mount temporary directories below /var or
        # /tmp, which can itself be a symbolic link at the filesystem root.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'source'
            root.mkdir()
            (root / 'visible.txt').touch()
            anchor = Path(root.anchor)
            system_alias = next(p for p in root.absolute().parents if p.parent == anchor)
            with patch.object(Path, 'is_symlink', autospec=True,
                              side_effect=lambda path: path == system_alias):
                problems = []
                entries = list(walk_project(root, problems))
            self.assertEqual(entries[0][2], ['visible.txt'])
            self.assertEqual(problems, [])

    def test_normal_nested_root_is_scanned(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'project' / 'source'
            root.mkdir(parents=True)
            (root / 'visible.txt').touch()
            problems = []
            files = list(walk_project(root, problems))
            self.assertEqual(files[0][2], ['visible.txt'])
            self.assertEqual(problems, [])


if __name__ == '__main__':
    unittest.main()
