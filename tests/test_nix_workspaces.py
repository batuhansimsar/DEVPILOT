"""Regression coverage for flake and legacy Nix workspace detection."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class NixWorkspacesTests(unittest.TestCase):
    def test_flake_legacy_and_lock_only_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = (
                ('app', ('flake.nix', 'flake.lock')),
                ('shell', ('shell.nix',)),
                ('legacy', ('default.nix',)),
                ('lock-only', ('flake.lock',)),
            )
            for project, files in cases:
                workspace = root / project
                workspace.mkdir()
                for name in files:
                    (workspace / name).write_text('', encoding='utf-8')
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 4)
            for entry in report['workspaces']:
                self.assertEqual(entry['ecosystems'], ['Nix'])
                self.assertEqual(
                    {manifest['file'] for manifest in entry['manifests']},
                    set(dict(cases)[entry['path']]),
                )

    def test_mixed_ecosystems_and_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ('flake.nix', 'go.mod', 'flake.nix.bak', 'shell.nix~', 'not-flake.nix'):
                (root / filename).write_text('', encoding='utf-8')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Go', 'Nix'])
            self.assertEqual(
                [m['file'] for m in report['workspaces'][0]['manifests']],
                ['flake.nix', 'go.mod'],
            )

    def test_symlinked_flake_is_not_inspected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'flake.nix'
            target.write_text('', encoding='utf-8')
            try:
                (root / 'flake.nix').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_applies_to_nix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            (root / 'nested' / 'flake.nix').write_text('', encoding='utf-8')
            limited = discover_workspaces(root, max_depth=0)
            self.assertTrue(limited['truncated'])
            self.assertEqual(limited['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
