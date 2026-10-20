"""Git porcelain v1 validation must not turn diagnostics into dirty worktrees."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.git_state import is_git_dirty


class GitDirtyValidationTests(unittest.TestCase):
    def test_non_porcelain_text_is_unknown(self):
        for output in (
            'fatal: not a git repository\n',
            '## main\nwarning: status output truncated\n',
            '## main\ngarbled tail\n',
            ' M\n',
            ' M \n',
            '??\n',
            ' Afilename\n',  # missing separator after XY status
            ' Z filename\n',  # unsupported status code
            '   whitespace\n',
        ):
            with self.subTest(output=output):
                self.assertIsNone(is_git_dirty(output, 0))

    def test_genuine_porcelain_records_remain_dirty(self):
        for record in (
            ' M edited.txt\n',
            'M  staged.txt\n',
            '?? untracked.txt\n',
            'UU conflict.txt\n',
            'R  old.txt -> new.txt\n',
            ' T changed-type.txt\n',
            '?? pending.txt',  # truncated after an otherwise complete status record
        ):
            with self.subTest(record=record):
                self.assertIs(is_git_dirty('## main\n' + record, 0), True)

    def test_ignored_records_are_not_dirty_without_real_changes(self):
        # Porcelain v1's !! denotes ignored paths, not tracked changes.
        self.assertIs(is_git_dirty('## main\n!! ignored.txt\n', 0), False)
        self.assertIs(is_git_dirty('## main\n!! ignored.txt\n!! cache/\n', 0), False)
        self.assertIs(is_git_dirty('## main\n!! ignored.txt\n M changed.py\n', 0), True)
        # A torn ignored-file record is not evidence of a clean worktree.
        self.assertIsNone(is_git_dirty('## main\n!! ignored.txt', 0))

    def test_genuine_status_after_broken_prefix_is_dirty(self):
        self.assertIs(is_git_dirty('fragment\n M edited.txt\n', 0), True)

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_real_git_status_clean_and_dirty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)

            def status():
                result = subprocess.run(
                    ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                     'status', '--porcelain=v1', '--branch'],
                    cwd=root, check=True, capture_output=True, text=True,
                )
                return is_git_dirty(result.stdout, result.returncode)

            self.assertIs(status(), False)
            (root / 'added.txt').write_text('sample', encoding='utf-8')
            self.assertIs(status(), True)
            subprocess.run(['git', 'add', 'added.txt'], cwd=root, check=True)
            self.assertIs(status(), True)

    def test_malformed_header_is_not_a_status(self):
        self.assertIsNone(is_git_dirty('##ma\n M edited.txt\n', 0))


if __name__ == '__main__':
    unittest.main()
