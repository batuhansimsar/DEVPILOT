"""Zig workspace detection: project recipes, dependency manifests, and safety."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class ZigWorkspaceTests(unittest.TestCase):
    def test_nested_build_recipe_and_dependency_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recipe = root / 'apps' / 'cli'
            recipe.mkdir(parents=True)
            (recipe / 'build.zig').write_text('// Zig build script\n')
            (recipe / 'build.zig.zon').write_text('.{}\n')
            library = root / 'libs' / 'math'
            library.mkdir(parents=True)
            (library / 'build.zig.zon').write_text('.{}\n')

            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 2)
            self.assertEqual(
                [(item['path'], item['ecosystems']) for item in report['workspaces']],
                [('apps/cli', ['Zig']), ('libs/math', ['Zig'])],
            )
            self.assertEqual(
                report['workspaces'][0]['manifests'],
                [{'file': 'build.zig', 'ecosystem': 'Zig'},
                 {'file': 'build.zig.zon', 'ecosystem': 'Zig'}],
            )

    def test_unrelated_files_and_backup_copies_do_not_create_projects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for filename in ('build.zig.bak', 'build.zig.zon.old', 'build.zig.txt', 'README.md'):
                (root / filename).write_text('')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_symlinked_zig_manifest_is_not_read(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as external:
            root = Path(temporary)
            original = Path(external) / 'build.zig'
            original.write_text('')
            try:
                (root / 'build.zig').symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_applies_to_zig(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / 'zig-app'
            nested.mkdir()
            (nested / 'build.zig').write_text('')
            limited = discover_workspaces(root, max_depth=0)
            self.assertTrue(limited['truncated'])
            self.assertEqual(limited['workspace_count'], 0)
            self.assertEqual(discover_workspaces(root, max_depth=1)['workspace_count'], 1)


if __name__ == '__main__':
    unittest.main()
