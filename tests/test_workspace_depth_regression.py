import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class WorkspaceDepthRegressionTests(unittest.TestCase):
    def test_depth_limit_reports_incomplete_scan(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested' / 'too-deep').mkdir(parents=True)
            (root / 'nested' / 'too-deep' / 'go.mod').write_text('module deep')
            result = discover_workspaces(root, max_depth=1)
            self.assertTrue(result['truncated'])
            self.assertEqual(result['workspace_count'], 0)
            self.assertEqual(result['directories_scanned'], 2)

    def test_exact_depth_with_no_children_is_complete(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'nested').mkdir()
            (root / 'nested' / 'go.mod').write_text('module nested')
            result = discover_workspaces(root, max_depth=1)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['workspace_count'], 1)

    def test_skipped_directories_do_not_mark_incomplete(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'package.json').write_text('{}')
            result = discover_workspaces(root, max_depth=0)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['directories_scanned'], 1)

    def test_limit_preserves_sibling_results(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a' / 'deeper').mkdir(parents=True)
            (root / 'z').mkdir()
            (root / 'z' / 'package.json').write_text('{}')
            result = discover_workspaces(root, max_depth=1)
            self.assertTrue(result['truncated'])
            self.assertEqual([w['path'] for w in result['workspaces']], ['z'])


if __name__ == '__main__':
    unittest.main()
