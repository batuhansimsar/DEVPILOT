"""Scan warnings must distinguish literal escape spellings from control characters."""

import errno
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import _printable, walk_project


class WalkBackslashDisambiguationTests(unittest.TestCase):
    def test_literal_escape_spellings_cannot_impersonate_control_characters(self):
        self.assertEqual(_printable('name\n.txt'), r'name\u000a.txt')
        self.assertEqual(_printable(r'name\u000a.txt'), r'name\\u000a.txt')
        self.assertNotEqual(_printable('name\n.txt'), _printable(r'name\u000a.txt'))
        self.assertEqual(_printable('name\u202e.txt'), r'name\u202e.txt')
        self.assertEqual(_printable(r'name\u202e.txt'), r'name\\u202e.txt')
        self.assertEqual(_printable('café/README.md'), 'café/README.md')

    def test_read_error_with_literal_backslash_is_not_misleading(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'secret diagnostic', str(root / r'src\u000a')))
            return iter(())

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            self.assertEqual(list(walk_project(root, problems)), [])
        self.assertEqual(problems, [r'Cannot inspect src\\u000a: Permission denied'])
        self.assertNotIn('secret diagnostic', problems[0])


if __name__ == '__main__':
    unittest.main()
