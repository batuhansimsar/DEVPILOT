"""Deno lockfiles independently identify read-only workspace boundaries."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class DenoLockfileWorkspaceTests(unittest.TestCase):
    def test_standalone_lockfile_in_nested_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / 'apps' / 'api'
            nested.mkdir(parents=True)
            (nested / 'deno.lock').write_text('{"version": "4"}', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['path'], 'apps/api')
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Deno'])
        self.assertEqual(report['workspaces'][0]['manifests'],
                         [{'file': 'deno.lock', 'ecosystem': 'Deno'}])

    def test_lockfile_and_config_count_as_one_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'deno.json').write_text('{}', encoding='utf-8')
            (root / 'deno.lock').write_text('{}', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Deno'])
        self.assertEqual([m['file'] for m in report['workspaces'][0]['manifests']],
                         ['deno.json', 'deno.lock'])

    def test_symlinked_lockfile_is_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as other:
            root = Path(temp)
            outside = Path(other) / 'deno.lock'
            outside.write_text('{}', encoding='utf-8')
            try:
                (root / 'deno.lock').symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_backup_like_names_do_not_trigger_detection(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'deno.lock.bak').write_text('{}', encoding='utf-8')
            (root / 'deno.lock.old').write_text('{}', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
