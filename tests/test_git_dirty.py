"""Regression coverage for the Git dirty-worktree signal used by automation."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.git_state import is_git_dirty


class GitDirtyTests(unittest.TestCase):
    def test_clean_branch_headers(self):
        self.assertFalse(is_git_dirty('## main\n', 0))
        self.assertFalse(is_git_dirty('## No commits yet on main\n', 0))

    def test_staged_unstaged_and_untracked_changes(self):
        for status in (' M app.py', 'M  staged.py', '?? new.txt', 'UU conflicted.txt', 'R  moved.py -> renamed.py'):
            with self.subTest(status=status):
                self.assertTrue(is_git_dirty('## main\n' + status + '\n', 0))

    def test_failure_is_unknown_not_clean(self):
        self.assertIsNone(is_git_dirty('', 128))
        self.assertIsNone(is_git_dirty('## main\n', None))

    def test_output_tail_still_detects_changes(self):
        self.assertTrue(is_git_dirty('ile\n M path.py\n', 0))

    def test_real_git_porcelain(self):
        if not shutil.which('git'):
            self.skipTest('Git is not installed')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            def status():
                output = subprocess.run([
                    'git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                    'status', '--porcelain=v1', '--branch', '--untracked-files=normal',
                ], cwd=root, capture_output=True, text=True, check=True)
                return is_git_dirty(output.stdout, output.returncode)
            self.assertFalse(status())
            (root / 'new.txt').write_text('test', encoding='utf-8')
            self.assertTrue(status())
            subprocess.run(['git', 'add', 'new.txt'], cwd=root, check=True)
            self.assertTrue(status())


if __name__ == '__main__':
    unittest.main()
