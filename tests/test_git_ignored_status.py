"""Ignored Git files must not incorrectly mark a working tree as dirty."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.git_state import is_git_dirty


class GitIgnoredStatusTests(unittest.TestCase):
    def test_ignored_entries_alone_are_clean(self):
        self.assertIs(is_git_dirty('## main\n!! .cache/\n', 0), False)
        self.assertIs(is_git_dirty('## main\n!! .cache/\n!! build.tmp\n', 0), False)

    def test_ignored_entries_do_not_hide_actual_changes(self):
        self.assertIs(is_git_dirty('## main\n!! build/\n?? new.txt\n', 0), True)
        self.assertIs(is_git_dirty('## main\n M app.py\n!! build/\n', 0), True)

    def test_incomplete_or_malformed_ignored_output_is_unknown(self):
        for output in ('## main\n!! ', '## main\n!! build',
                       '!! build/\n', '## main\n!!\n',
                       '## main\n!! build/\nfragment\n'):
            with self.subTest(output=output):
                self.assertIsNone(is_git_dirty(output, 0))

    @unittest.skipUnless(shutil.which('git'), 'Git is not installed')
    def test_real_git_ignored_and_untracked_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            (root / '.gitignore').write_text('*.tmp\n', encoding='utf-8')
            subprocess.run(['git', 'add', '.gitignore'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=DevPilot Test',
                            '-c', 'user.email=test@example.invalid',
                            'commit', '-qm', 'baseline'], cwd=root, check=True)
            (root / 'cache.tmp').write_text('ignored', encoding='utf-8')

            def status():
                result = subprocess.run(
                    ['git', '-c', 'core.fsmonitor=false', '--no-optional-locks',
                     'status', '--porcelain=v1', '--branch', '--ignored'],
                    cwd=root, capture_output=True, text=True, check=True,
                )
                return is_git_dirty(result.stdout, result.returncode)

            self.assertIs(status(), False)
            (root / 'untracked.txt').write_text('new', encoding='utf-8')
            self.assertIs(status(), True)


if __name__ == '__main__':
    unittest.main()
