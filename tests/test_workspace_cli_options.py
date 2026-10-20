"""CLI regression coverage for bounded monorepo discovery."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.cli import main


class WorkspaceCliOptionsTests(unittest.TestCase):
    def invoke(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main(['workspaces', *args, '--json'])
        self.assertEqual(status, 0)
        return json.loads(out.getvalue())

    def test_depth_zero_limits_discovery_to_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'go.mod').write_text('module root')
            nested = root / 'apps' / 'web'
            nested.mkdir(parents=True)
            (nested / 'package.json').write_text('{}')
            result = self.invoke('--path', directory, '--max-depth', '0')
            self.assertEqual([entry['path'] for entry in result['workspaces']], ['.'])
            self.assertFalse(result['truncated'])
            result = self.invoke('--path', directory, '--max-depth', '2')
            self.assertEqual([entry['path'] for entry in result['workspaces']], ['.', 'apps/web'])

    def test_directory_budget_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            (root / 'nested' / 'go.mod').write_text('module nested')
            result = self.invoke('--path', directory, '--max-directories', '1')
            self.assertTrue(result['truncated'])
            self.assertEqual(result['directories_scanned'], 1)
            self.assertEqual(result['workspace_count'], 0)

    def test_rejects_invalid_limits_before_scanning(self):
        with tempfile.TemporaryDirectory() as directory:
            for flag, value in (('--max-depth', '-1'), ('--max-depth', '51'),
                                ('--max-directories', '0'), ('--max-directories', '100001')):
                with self.subTest(flag=flag, value=value):
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        main(['workspaces', '--path', directory, flag, value])
                    self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
