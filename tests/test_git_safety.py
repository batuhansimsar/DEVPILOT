"""Ensure read-only Git inspection cannot launch a configured fsmonitor hook."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import git_status


class GitStatusSafetyTests(unittest.TestCase):
    def test_git_invocation_disables_fsmonitor_and_optional_locks(self):
        with patch('devpilot.core.command_result', return_value={'exit_code': 0, 'stdout': '', 'stderr': ''}) as execute:
            git_status(Path('/example'))
        args = execute.call_args.args[0]
        self.assertEqual(args[0], 'git')
        self.assertIn('--no-optional-locks', args)
        self.assertIn('core.fsmonitor=false', args)
        self.assertLess(args.index('core.fsmonitor=false'), args.index('status'))

    @unittest.skipIf(os.name == 'nt' or not shutil.which('git'), 'requires POSIX shell and git')
    def test_git_status_does_not_execute_fsmonitor_hook(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'tracked.txt').write_text('sample', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', 'tracked.txt'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=DevPilot',
                            '-c', 'user.email=devpilot@example.invalid', 'commit', '-qm', 'init'], check=True)
            marker = root / 'hook-executed'
            hook = root / 'monitor.sh'
            hook.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n', encoding='utf-8')
            hook.chmod(0o700)
            subprocess.run(['git', '-C', str(root), 'config', 'core.fsmonitor', str(hook)], check=True)
            result = git_status(root)
            self.assertEqual(result['exit_code'], 0, result.get('stderr'))
            self.assertFalse(marker.exists(), 'Git unexpectedly executed an untrusted fsmonitor')
            self.assertIn('## ', result['stdout'])


if __name__ == '__main__':
    unittest.main()
