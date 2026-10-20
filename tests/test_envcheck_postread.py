"""Regression coverage for concurrent mutation during .env inspection."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.envcheck import inspect_env


class EnvPostReadMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / '.env.example').write_text('TOKEN=example\n')
        (self.root / '.env').write_text('TOKEN=private\n')

    def test_template_mutated_during_read_is_unreadable(self):
        original_fstat = os.fstat
        count = 0

        def change_after_read(fd):
            nonlocal count
            count += 1
            if count == 2:
                with (self.root / '.env.example').open('ab') as out:
                    out.write(b'ADDED=value\n')
            return original_fstat(fd)

        with patch('devpilot.envcheck.os.fstat', side_effect=change_after_read):
            report = inspect_env(self.root)
        self.assertEqual(report['status'], 'unreadable_template')
        self.assertEqual(report['detail'], 'file changed during inspection')
        self.assertNotIn('private', str(report))

    def test_local_mutated_during_read_is_unreadable(self):
        original_fstat = os.fstat
        count = 0

        def change_after_read(fd):
            nonlocal count
            count += 1
            if count == 4:
                with (self.root / '.env').open('ab') as out:
                    out.write(b'ADDED=value\n')
            return original_fstat(fd)

        with patch('devpilot.envcheck.os.fstat', side_effect=change_after_read):
            report = inspect_env(self.root)
        self.assertEqual(report['status'], 'unreadable_local')
        self.assertEqual(report['detail'], 'file changed during inspection')

    def test_unchanged_files_still_match(self):
        self.assertEqual(inspect_env(self.root)['status'], 'matched')


if __name__ == '__main__':
    unittest.main()
