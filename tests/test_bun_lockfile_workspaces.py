"""Bun lockfiles are workspace markers even without a package.json file."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class BunLockfileWorkspaceTests(unittest.TestCase):
    def test_text_and_binary_bun_lockfiles_identify_node_workspaces(self):
        for lockfile in ('bun.lock', 'bun.lockb'):
            with self.subTest(lockfile=lockfile), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / lockfile).write_bytes(b'')
                report = discover_workspaces(root)
                self.assertEqual(report['workspace_count'], 1)
                self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])
                self.assertEqual(report['workspaces'][0]['manifests'], [
                    {'file': lockfile, 'ecosystem': 'Node.js'},
                ])

    def test_bun_lockfile_and_package_manifest_form_one_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'apps' / 'api'
            project.mkdir(parents=True)
            (project / 'package.json').write_text('{}')
            (project / 'bun.lock').write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'apps/api')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Node.js'])
            self.assertEqual([item['file'] for item in report['workspaces'][0]['manifests']],
                             ['bun.lock', 'package.json'])

    def test_symlinked_bun_lockfile_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside) / 'bun.lock'
            external.write_text('')
            try:
                (root / 'bun.lock').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks not supported')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_applies_to_bun_workspaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'nested'
            nested.mkdir()
            (nested / 'bun.lockb').write_bytes(b'')
            self.assertTrue(discover_workspaces(root, max_depth=0)['truncated'])
            self.assertEqual(discover_workspaces(root, max_depth=0)['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
