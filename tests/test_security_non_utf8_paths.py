"""Track each non-UTF-8 Git filename without lossy replacement or unsafe output."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.security import tracked_environment_files


@unittest.skipUnless(shutil.which('git'), 'Git is not installed')
class NonUTF8GitPathTests(unittest.TestCase):
    def test_invalid_utf8_bytes_remain_distinguishable(self):
        fake_paths = b'backend/.env.\xff\0backend/.env.\xfe\0'
        with patch('devpilot.security._tracked_paths', return_value=fake_paths):
            found = tracked_environment_files(Path('.'))
        self.assertEqual(found, [r'backend/.env.\udcfe', r'backend/.env.\udcff'])
        self.assertNotIn('\ufffd', ''.join(found))

    @unittest.skipIf(os.name == 'nt', 'Raw byte filename test is POSIX-only')
    def test_real_git_index_preserves_distinct_invalid_utf8_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for suffix in (b'\xfe', b'\xff'):
                filename = os.fsencode(str(root)) + b'/.env.' + suffix
                fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.close(fd)
            subprocess.run(['git', '-C', str(root), 'add', '--all'], check=True)
            self.assertEqual(tracked_environment_files(root), [r'.env.\udcfe', r'.env.\udcff'])


if __name__ == '__main__':
    unittest.main()
