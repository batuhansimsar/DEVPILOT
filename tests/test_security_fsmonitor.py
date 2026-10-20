"""Regression tests for safe, read-only discovery of tracked environment files."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.security import tracked_environment_files


@unittest.skipUnless(shutil.which('git'), 'Git is not installed')
class TrackedEnvironmentGitSafetyTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'POSIX executable hook fixture')
    def test_untrusted_fsmonitor_is_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.env.local').write_text('NEVER_PRINT_THIS', encoding='utf-8')
            (root / '.env.example').write_text('TEMPLATE', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '.env.local', '.env.example'], check=True)
            index = root / '.git' / 'index'
            before = index.stat().st_mtime_ns
            marker = root / 'fsmonitor-was-run'
            hook = root / 'fsmonitor.sh'
            hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n', encoding='utf-8')
            hook.chmod(0o700)
            subprocess.run(['git', '-C', str(root), 'config', 'core.fsmonitor', str(hook)], check=True)

            self.assertEqual(tracked_environment_files(root), ['.env.local'])
            self.assertFalse(marker.exists(), 'untrusted fsmonitor helper was executed')
            self.assertEqual(index.stat().st_mtime_ns, before)
            self.assertFalse((root / '.git' / 'index.lock').exists())


if __name__ == '__main__':
    unittest.main()
