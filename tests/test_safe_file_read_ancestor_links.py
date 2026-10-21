"""A regular manifest through a linked parent must never be read."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class BoundedFileLinkedAncestorsTests(unittest.TestCase):
    def test_refuses_manifest_under_linked_parent_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / 'external'
            nested = external / 'nested'
            nested.mkdir(parents=True)
            manifest = nested / 'package.json'
            manifest.write_bytes(b'{"private":true}')
            linked = root / 'alias'
            try:
                linked.symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unavailable')

            for candidate in (linked / 'nested' / 'package.json',
                              root / 'alias' / 'nested' / '..' / 'nested' / 'package.json'):
                with self.subTest(path=candidate), patch('devpilot.safe_file_read.os.open') as opened:
                    self.assertIsNone(read_bounded_regular_file(candidate, 128))
                    opened.assert_not_called()

            # Directly selected ordinary files remain readable.
            self.assertEqual(read_bounded_regular_file(manifest, 128), b'{"private":true}')


if __name__ == '__main__':
    unittest.main()
