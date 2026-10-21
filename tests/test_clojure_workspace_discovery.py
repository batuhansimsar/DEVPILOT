"""Clojure Leiningen and tools.deps workspaces are discovered safely."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class ClojureWorkspaceDiscoveryTests(unittest.TestCase):
    def test_nested_tools_deps_and_leiningen_projects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path, manifest in (
                ('services/api', 'deps.edn'),
                ('services/batch', 'project.clj'),
            ):
                workspace = root / path
                workspace.mkdir(parents=True)
                (workspace / manifest).write_text('', encoding='utf-8')
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(report['workspace_count'], 2)
            self.assertEqual(
                [(w['path'], w['ecosystems']) for w in report['workspaces']],
                [('services/api', ['Clojure']), ('services/batch', ['Clojure'])],
            )
            self.assertEqual(
                [w['manifests'][0]['file'] for w in report['workspaces']],
                ['deps.edn', 'project.clj'],
            )

    def test_multiple_clojure_manifests_in_one_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ('deps.edn', 'project.clj', 'readme.txt'):
                (root / filename).write_text('', encoding='utf-8')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Clojure'])
            self.assertEqual(
                [m['file'] for m in report['workspaces'][0]['manifests']],
                ['deps.edn', 'project.clj'],
            )

    def test_symlinked_manifest_does_not_count(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'deps.edn'
            target.write_text('', encoding='utf-8')
            try:
                (root / 'deps.edn').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_depth_limit_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'nested'
            nested.mkdir()
            (nested / 'project.clj').write_text('', encoding='utf-8')
            (nested / 'project.clj.bak').write_text('', encoding='utf-8')
            limited = discover_workspaces(root, max_depth=0)
            self.assertTrue(limited['truncated'])
            self.assertEqual(limited['workspace_count'], 0)
            allowed = discover_workspaces(root, max_depth=1)
            self.assertEqual(allowed['workspace_count'], 1)
            self.assertEqual(len(allowed['workspaces'][0]['manifests']), 1)


if __name__ == '__main__':
    unittest.main()
