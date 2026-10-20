"""Regression tests for untrusted env-file read races and secret handling."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.envcheck import MAX_ENV_BYTES, _keys, inspect_env


class EnvReadSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_normal_env_comparison_only_reports_names(self):
        (self.root / '.env.example').write_text('TOKEN=sample\nHOST=local\n')
        (self.root / '.env').write_text('TOKEN=secret-should-not-leak\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'missing_keys')
        self.assertEqual(report['missing_keys'], ['HOST'])
        self.assertNotIn('secret-should-not-leak', repr(report))

    def test_existing_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / 'secrets.env'
            secret.write_text('SECRET=private')
            try:
                (self.root / '.env').symlink_to(secret)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks not supported')
            self.assertEqual(_keys(self.root / '.env'), (None, 'not a regular file'))

    def test_regular_file_replaced_between_stat_and_open(self):
        path = self.root / '.env'
        path.write_text('SAFE=1')
        real_open = os.open
        def swap(name, flags):
            path.rename(self.root / 'old.env')
            path.write_text('SECRET=2')
            return real_open(name, flags)
        with patch('devpilot.envcheck.os.open', side_effect=swap):
            result = _keys(path)
        self.assertEqual(result, (None, 'changed during inspection'))

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'platform lacks O_NOFOLLOW')
    def test_late_symlink_swap_is_rejected(self):
        path = self.root / '.env'
        path.write_text('SAFE=1')
        secret = self.root / 'hidden.txt'
        secret.write_text('SECRET=2')
        real_open = os.open
        def swap(name, flags):
            path.unlink()
            path.symlink_to(secret)
            return real_open(name, flags)
        with patch('devpilot.envcheck.os.open', side_effect=swap):
            result = _keys(path)
        self.assertEqual(result, (None, 'not readable'))

    def test_grown_env_file_is_bounded(self):
        path = self.root / '.env'
        path.write_text('SAFE=1')
        real_open = os.open
        def grow(name, flags):
            path.write_bytes(b'x' * (MAX_ENV_BYTES + 1))
            return real_open(name, flags)
        with patch('devpilot.envcheck.os.open', side_effect=grow):
            result = _keys(path)
        self.assertEqual(result, (None, 'exceeds 256 KiB limit'))

    def test_in_place_rewrite_during_read_is_rejected(self):
        path = self.root / '.env'
        path.write_text('TOKEN=value\n', encoding='utf-8')
        original_fstat = os.fstat
        calls = 0

        def rewrite_before_final_check(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                old = path.stat()
                path.write_text('TOKEN=other\n', encoding='utf-8')
                os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns + 5_000_000_000))
            return original_fstat(fd)

        with patch('devpilot.envcheck.os.fstat', side_effect=rewrite_before_final_check):
            result = _keys(path)
        self.assertEqual(result, (None, 'file changed during inspection'))


    def test_in_place_growth_after_open_is_bounded(self):
        path = self.root / '.env'
        path.write_text('SAFE=1', encoding='utf-8')
        original_fstat = os.fstat
        calls = 0

        def grow_before_final_check(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                path.write_bytes(b'x' * (MAX_ENV_BYTES + 1))
            return original_fstat(fd)

        with patch('devpilot.envcheck.os.fstat', side_effect=grow_before_final_check):
            result = _keys(path)
        self.assertEqual(result, (None, 'exceeds 256 KiB limit'))


if __name__ == '__main__':
    unittest.main()
