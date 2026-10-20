"""Regression tests for inspecting Git workspaces with unsafe local config."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core


@unittest.skipUnless(shutil.which('git'), 'Git is not installed')
class GitStatusSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)

    def test_status_preserves_untracked_file_discovery(self):
        (self.root / 'new.txt').write_text('untracked')
        report = core.git_status(self.root)
        self.assertEqual(report['exit_code'], 0, report.get('stderr'))
        self.assertIn('?? new.txt', report['stdout'])

    def test_git_status_disables_repo_hooks_and_optional_locks(self):
        with patch.object(core, 'command_result', return_value={
                'exit_code': 0, 'stdout': '', 'stderr': ''}) as run:
            core.git_status(self.root)
        argv = run.call_args.args[0]
        self.assertEqual(argv[0:4], [
            'git', '--no-optional-locks', '-c', 'core.fsmonitor=false'])
        self.assertEqual(argv[4], 'status')

    @unittest.skipIf(os.name == 'nt', 'POSIX shell fixture')
    def test_repo_fsmonitor_is_never_executed_or_index_rewritten(self):
        (self.root / 'tracked.txt').write_text('committed')
        subprocess.run(['git', 'add', 'tracked.txt'], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.name=DevPilot Test',
                        '-c', 'user.email=test@example.invalid',
                        'commit', '-qm', 'baseline'], cwd=self.root, check=True)
        index = self.root / '.git' / 'index'
        before = index.stat().st_mtime_ns
        hook = self.root / 'fsmonitor.sh'
        hook.write_text('#!/bin/sh\ntouch fsmonitor-was-executed\n')
        hook.chmod(0o700)
        subprocess.run(['git', 'config', 'core.fsmonitor', './fsmonitor.sh'],
                       cwd=self.root, check=True)

        report = core.git_status(self.root)
        self.assertEqual(report['exit_code'], 0, report.get('stderr'))
        self.assertFalse((self.root / 'fsmonitor-was-executed').exists())
        self.assertEqual(index.stat().st_mtime_ns, before)
        self.assertFalse((self.root / '.git' / 'index.lock').exists())


if __name__ == '__main__':
    unittest.main()
