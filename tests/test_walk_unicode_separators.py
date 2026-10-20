"""Non-control Unicode separators and astral format characters are also unsafe in logs."""

import errno
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.walk import walk_project


class WalkUnicodeSeparatorTests(unittest.TestCase):
    def test_unicode_line_separators_and_astral_format_are_escaped(self):
        root = Path.cwd() / 'example'
        problems = []
        hostile = 'secret\u2028new-line\u2029new-paragraph\U000e0001'

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'failed', str(root / hostile)))
            return iter(())

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            list(walk_project(root, problems))

        self.assertEqual(problems, [
            r'Cannot inspect secret\u2028new-line\u2029new-paragraph\U000e0001: failed'
        ])
        for invisible in ('\u2028', '\u2029', '\U000e0001'):
            self.assertNotIn(invisible, problems[0])

    def test_readable_unicode_is_preserved(self):
        root = Path.cwd() / 'example'
        problems = []

        def fake_walk(path, *, followlinks, onerror):
            onerror(OSError(errno.EACCES, 'Giriş engellendi', str(root / 'çalışma')))
            return iter(())

        with patch('devpilot.walk.os.walk', side_effect=fake_walk):
            list(walk_project(root, problems))
        self.assertEqual(problems, ['Cannot inspect çalışma: Giriş engellendi'])


if __name__ == '__main__':
    unittest.main()
