"""Bundler's gems.rb uses gems.locked rather than Gemfile.lock."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan
from devpilot.workspaces import discover_workspaces


LOCK = (
    'GEM\n'
    '  remote: https://user:private-token@registry.example.test/\n'
    '  specs:\n'
    '    Rails (7.1.0)\n'
    '      rack (~> 3)\n'
    '    my_gem (2.0)\n'
    'DEPENDENCIES\n'
    '  Rails\n'
)


class BundlerAlternateLockfileTests(unittest.TestCase):
    def test_gems_locked_only_workspace_is_detected_and_inventoried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gems.locked').write_text(LOCK, encoding='utf-8')
            inventory = scan(root)
            workspaces = discover_workspaces(root)

        self.assertEqual(inventory['warnings'], [])
        self.assertEqual(inventory['totals'], {'Ruby': 2})
        self.assertEqual(inventory['manifests'], [{
            'path': 'gems.locked',
            'ecosystem': 'Ruby',
            'groups': {'locked': ['my-gem', 'rails']},
            'count': 2,
        }])
        self.assertEqual(workspaces['workspace_count'], 1)
        self.assertEqual(workspaces['workspaces'][0]['manifests'],
                         [{'file': 'gems.locked', 'ecosystem': 'Ruby'}])
        self.assertNotIn('private-token', json.dumps(inventory))

    def test_nested_gems_locked_and_gems_rb_are_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'service'
            nested.mkdir()
            (nested / 'gems.rb').write_text("gem 'rails'\n", encoding='utf-8')
            (nested / 'gems.locked').write_text(LOCK, encoding='utf-8')
            inventory = scan(root)
            workspaces = discover_workspaces(root)

        self.assertEqual([item['path'] for item in inventory['manifests']],
                         ['service/gems.locked'])
        self.assertEqual(inventory['totals'], {'Ruby': 2})
        self.assertEqual(workspaces['workspaces'][0]['path'], 'service')
        self.assertEqual([item['file'] for item in workspaces['workspaces'][0]['manifests']],
                         ['gems.locked', 'gems.rb'])

    def test_symlinked_gems_locked_is_not_read(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            secret_file = Path(other) / 'gems.locked'
            secret_file.write_text(LOCK, encoding='utf-8')
            try:
                (root / 'gems.locked').symlink_to(secret_file)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks unsupported')

            self.assertEqual(scan(root)['manifests'], [])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
