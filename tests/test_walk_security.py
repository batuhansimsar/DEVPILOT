"""Regression tests for safe, readable directory-scan diagnostics."""

import errno
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import walk_project


class WalkErrorTerminalSafetyTests(unittest.TestCase):
    def test_untrusted_directory_name_cannot_emit_terminal_controls(self):
        root = Path.cwd() / 'example'
        problems = []
        hostile = 'hidden\n\x1b[31m\u202e'

        def fake_walk(path, *, followlinks, onerror):
            self.assertEqual(path, root)
            self.assertFalse(followlinks)
            onerror(PermissionError(errno.EACCES, 'Permission denied', str(root / hostile)))
            return iter(())

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            self.assertEqual(list(walk_project(root, problems)), [])
        self.assertEqual(problems, ['Cannot inspect hidden\\u000a\\u001b[31m\\u202e: Permission denied'])
        self.assertNotIn('\n', problems[0])
        self.assertNotIn('\x1b', problems[0])
        self.assertNotIn('\u202e', problems[0])

    def test_untrusted_error_detail_cannot_emit_terminal_controls(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'failed\x1b[0m\rupdate', str(root / 'private')))
            return iter(())

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            list(walk_project(root, problems))
        self.assertEqual(problems, ['Cannot inspect private: failed\\u001b[0m\\u000dupdate'])


if __name__ == '__main__':
    unittest.main()
