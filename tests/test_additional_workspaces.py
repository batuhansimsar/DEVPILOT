"""Regression coverage for Swift, Dart and Elixir workspace manifests."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class AdditionalWorkspaceTests(unittest.TestCase):
    def test_nested_swift_dart_and_elixir_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, manifest in (
                ('ios', 'Package.swift'),
                ('mobile', 'pubspec.yaml'),
                ('services', 'mix.exs'),
            ):
                workspace = root / name
                workspace.mkdir()
                (workspace / manifest).write_text('')
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 3)
            self.assertEqual(
                [(entry['path'], entry['ecosystems']) for entry in report['workspaces']],
                [('ios', ['Swift']), ('mobile', ['Dart']), ('services', ['Elixir'])],
            )
            self.assertEqual(
                [entry['manifests'][0]['file'] for entry in report['workspaces']],
                ['Package.swift', 'pubspec.yaml', 'mix.exs'],
            )

    def test_multiple_ecosystems_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('Package.swift', 'pubspec.yaml', 'mix.exs', 'notes.md'):
                (root / name).write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Dart', 'Elixir', 'Swift'])
            self.assertEqual(len(report['workspaces'][0]['manifests']), 3)

    def test_symlinked_manifest_is_never_counted(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'Package.swift'
            target.write_text('')
            try:
                (root / 'Package.swift').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limits_apply_to_new_ecosystems(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            (root / 'nested' / 'pubspec.yaml').write_text('')
            limited = discover_workspaces(root, max_depth=0)
            self.assertTrue(limited['truncated'])
            self.assertEqual(limited['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
