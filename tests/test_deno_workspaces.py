"""Deno project discovery through standard configuration manifests."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class DenoWorkspaceTests(unittest.TestCase):
    def test_deno_json_and_jsonc_in_nested_directories(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'deno.json').write_text('{}', encoding='utf-8')
            nested = root / 'packages' / 'api'
            nested.mkdir(parents=True)
            (nested / 'deno.jsonc').write_text('{ /* comments */ }', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual([w['path'] for w in report['workspaces']], ['.', 'packages/api'])
        self.assertEqual([w['ecosystems'] for w in report['workspaces']], [['Deno'], ['Deno']])
        self.assertEqual(report['workspaces'][1]['manifests'], [{'file': 'deno.jsonc', 'ecosystem': 'Deno'}])

    def test_deno_and_node_manifests_in_same_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'deno.json').write_text('{}', encoding='utf-8')
            (root / 'package.json').write_text('{}', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Deno', 'Node.js'])

    def test_deno_symlink_to_external_manifest_is_ignored(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as external:
            root = Path(temp)
            outside = Path(external) / 'deno.json'
            outside.write_text('{}', encoding='utf-8')
            try:
                (root / 'deno.json').symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
