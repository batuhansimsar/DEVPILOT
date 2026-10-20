"""Discover pip-tools inputs as Python workspaces without reading their contents."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class PipToolsWorkspaceTests(unittest.TestCase):
    def test_root_and_nested_requirements_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'requirements.in').write_text('requests>=2\n', encoding='utf-8')
            nested = root / 'service'
            nested.mkdir()
            (nested / 'requirements-dev.in').write_text('pytest>=8\n', encoding='utf-8')
            (nested / 'requirements-extra.txt').write_text('coverage\n', encoding='utf-8')
            (nested / 'requirements-other.ini').write_text('ignored\n', encoding='utf-8')
            (nested / 'constraints.in').write_text('ignored\n', encoding='utf-8')

            discovered = discover_workspaces(root)

        by_path = {item['path']: item for item in discovered['workspaces']}
        self.assertEqual(set(by_path), {'.', 'service'})
        self.assertEqual(by_path['.']['ecosystems'], ['Python'])
        self.assertEqual(by_path['service']['ecosystems'], ['Python'])
        self.assertEqual(
            {item['file'] for item in by_path['service']['manifests']},
            {'requirements-dev.in', 'requirements-extra.txt'},
        )
        self.assertFalse(discovered['truncated'])


if __name__ == '__main__':
    unittest.main()
