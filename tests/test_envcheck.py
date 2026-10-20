import os
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import patch

from devpilot.envcheck import MAX_ENV_BYTES, inspect_env


class EnvCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, text):
        (self.root / name).write_text(text, encoding='utf-8')

    def test_missing_keys_are_sorted_and_values_never_exposed(self):
        self.write('.env.example', '# ignored=bad\nexport TOKEN=top-secret\nDB_URL=postgres://example\n')
        self.write('.env', 'TOKEN=live-secret\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'missing_keys')
        self.assertEqual(result['missing_keys'], ['DB_URL'])
        self.assertNotIn('secret', str(result))
        self.assertNotIn('postgres://', str(result))

    def test_absent_local_is_informational(self):
        self.write('.env.sample', 'API_KEY=value\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'local_absent')
        self.assertNotIn('missing_keys', result)

    def test_template_size_limit(self):
        (self.root / '.env.example').write_bytes(b'x' * (MAX_ENV_BYTES + 1))
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')
        self.assertIn('limit', result['detail'])

    def test_symlinks_not_read(self):
        other = Path(self.tmp.name) / 'value'
        other.write_text('SECRET=private', encoding='utf-8')
        try:
            (self.root / '.env.example').symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks not available')
        self.assertEqual(inspect_env(self.root)['status'], 'unreadable_template')

    def test_empty_or_missing_template(self):
        self.assertEqual(inspect_env(self.root)['status'], 'no_template')
        self.write('.env.example', '# comment only\n')
        self.write('.env', 'IGNORED=yes\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['expected_count'], 0)

    def test_template_swap_to_symlink_is_rejected(self):
        self.write('.env.example', 'SAFE=value\n')
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'secret'
            target.write_text('SECRET=external-secret\n', encoding='utf-8')
            original_open = os.open
            def swap(path, flags):
                Path(path).unlink()
                Path(path).symlink_to(target)
                return original_open(path, flags)
            try:
                with patch('devpilot.envcheck.os.open', side_effect=swap):
                    result = inspect_env(self.root)
            except (NotImplementedError, OSError):
                self.skipTest('symlinks unavailable')
        self.assertEqual(result['status'], 'unreadable_template')
        self.assertNotIn('external-secret', str(result))

    def test_local_swap_to_symlink_is_rejected(self):
        self.write('.env.example', 'TOKEN=example\n')
        self.write('.env', 'TOKEN=local\n')
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'secret'
            target.write_text('TOKEN=external-secret\n', encoding='utf-8')
            original_open = os.open
            def swap(path, flags):
                if Path(path).name == '.env':
                    Path(path).unlink()
                    Path(path).symlink_to(target)
                return original_open(path, flags)
            try:
                with patch('devpilot.envcheck.os.open', side_effect=swap):
                    result = inspect_env(self.root)
            except (NotImplementedError, OSError):
                self.skipTest('symlinks unavailable')
        self.assertEqual(result['status'], 'unreadable_local')
        self.assertNotIn('external-secret', str(result))

    @unittest.skipUnless(hasattr(os, 'mkfifo') and hasattr(os, 'O_NONBLOCK'), 'POSIX FIFO required')
    def test_swap_to_fifo_is_rejected_without_blocking(self):
        self.write('.env.example', 'TOKEN=example\n')
        original_open = os.open
        def swap(path, flags):
            Path(path).unlink()
            os.mkfifo(path)
            return original_open(path, flags)
        with patch('devpilot.envcheck.os.open', side_effect=swap):
            result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')

    def test_growth_between_stat_and_open_is_rejected(self):
        self.write('.env.example', 'SAFE=example\n')
        original_open = os.open
        def grow(path, flags):
            Path(path).write_bytes(b'X' * (MAX_ENV_BYTES + 1))
            return original_open(path, flags)
        with patch('devpilot.envcheck.os.open', side_effect=grow):
            result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')


    def test_swap_to_another_regular_file_with_reused_inode_is_rejected(self):
        self.write('.env.example', 'EXPECTED=x\n')
        original_open = os.open

        def replace_regular_file(path, flags):
            Path(path).unlink()
            Path(path).write_text('UNTRUSTED_KEY=unexpected-content\n', encoding='utf-8')
            return original_open(path, flags)

        with patch('devpilot.envcheck.os.open', side_effect=replace_regular_file):
            result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')
        self.assertEqual(result['detail'], 'file changed during inspection')



    def test_template_swap_after_lstat_is_not_read(self):
        self.write('.env.example', 'PUBLIC=ok\n')
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / 'secret'
            external.write_text('PRIVATE_KEY=do-not-read\n', encoding='utf-8')
            target = self.root / '.env.example'
            original_lstat = Path.lstat
            swapped = False

            def swap_after_stat(path):
                nonlocal swapped
                metadata = original_lstat(path)
                if path == target and not swapped:
                    target.unlink()
                    try:
                        target.symlink_to(external)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks not available')
                    swapped = True
                return metadata

            with patch.object(Path, 'lstat', autospec=True, side_effect=swap_after_stat):
                result = inspect_env(self.root)
            self.assertEqual(result['status'], 'unreadable_template')
            self.assertNotIn('PRIVATE_KEY', str(result))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires named pipes')
    def test_fifo_swap_does_not_block_or_read(self):
        self.write('.env.example', 'PUBLIC=ok\n')
        target = self.root / '.env.example'
        original_lstat = Path.lstat
        swapped = False

        def swap_after_stat(path):
            nonlocal swapped
            metadata = original_lstat(path)
            if path == target and not swapped:
                target.unlink()
                os.mkfifo(target)
                swapped = True
            return metadata

        with patch.object(Path, 'lstat', autospec=True, side_effect=swap_after_stat):
            result = inspect_env(self.root)
        self.assertEqual(result['status'], 'unreadable_template')


if __name__ == '__main__':
    unittest.main()
