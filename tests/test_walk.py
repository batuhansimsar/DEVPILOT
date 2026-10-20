"""Directory read error reporting regression tests."""

import errno
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import walk_project


class WalkProjectTests(unittest.TestCase):
    def test_reports_permission_failure_and_continues(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            self.assertEqual(path, root)
            self.assertFalse(followlinks)
            onerror(PermissionError(errno.EACCES, 'Permission denied', str(root / 'private')))
            yield str(root), [], ['README.md']

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            files = list(walk_project(root, problems))
        self.assertEqual(files, [(str(root), [], ['README.md'])])
        self.assertEqual(problems, ['Cannot inspect private: Permission denied'])

    def test_redacts_outside_project_paths(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'Permission denied', str(root.parent / 'private' / 'secrets')))
            return iter([])

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            self.assertEqual(list(walk_project(root, problems)), [])
        self.assertEqual(problems, ['Cannot inspect [outside project]: Permission denied'])

    def test_no_errors_for_successful_walk(self):
        root = Path.cwd() / 'example'
        problems = []
        with patch('devpilot.walk.os.walk', return_value=iter([(str(root), [], [])])):
            self.assertEqual(list(walk_project(root, problems)), [(str(root), [], [])])
        self.assertEqual(problems, [])



    def test_terminal_controls_and_bidi_are_escaped(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'Permission\x1b[2J denied\u202e',
                            str(root / 'bad\nname\x1b[31m')))
            return iter([])

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            self.assertEqual(list(walk_project(root, problems)), [])
        self.assertEqual(problems, [
            r'Cannot inspect bad\u000aname\u001b[31m: Permission denied'
        ])
        self.assertFalse(any('\x1b' in issue or '\n' in issue or '\u202e' in issue
                             for issue in problems))

if __name__ == '__main__':
    unittest.main()
