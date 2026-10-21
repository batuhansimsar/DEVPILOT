"""Test discovery must not inspect or select commands from linked project roots."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import test_commands


class TestCommandRootSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / 'project'
        self.project.mkdir()
        (self.project / 'package.json').write_text(
            '{"scripts":{"test":"node --test"}}\n', encoding='utf-8'
        )

    def link(self, source: Path, target: Path):
        try:
            source.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('directory symlinks unavailable')

    def test_symlinked_project_root_is_rejected_before_manifest_inspection(self):
        alias = self.base / 'project-alias'
        self.link(alias, self.project)
        with patch('devpilot.core._root_files') as root_files, \
             patch('devpilot.core._read_package_json') as read_manifest:
            self.assertEqual(test_commands(alias), [])
        root_files.assert_not_called()
        read_manifest.assert_not_called()

    def test_symlinked_ancestor_is_rejected_before_manifest_inspection(self):
        outer = self.base / 'real-parent'
        outer.mkdir()
        nested = outer / 'nested'
        nested.mkdir()
        (nested / 'package.json').write_text('{"scripts":{"test":"echo test"}}')
        alias = self.base / 'parent-alias'
        self.link(alias, outer)
        with patch('devpilot.core._root_files') as root_files, \
             patch('devpilot.core._read_package_json') as read_manifest:
            self.assertEqual(test_commands(alias / 'nested'), [])
        root_files.assert_not_called()
        read_manifest.assert_not_called()

    def test_unlinked_project_retains_node_test_discovery(self):
        commands = test_commands(self.project)
        self.assertIn({'ecosystem': 'Node.js', 'argv': ['npm', 'test'],
                       'reason': 'package.json test script'}, commands)

    def test_os_error_during_root_validation_fails_closed(self):
        with patch('devpilot.core.ensure_unlinked_scan_path',
                   side_effect=OSError('private-path-data')), \
             patch('devpilot.core._root_files') as root_files:
            self.assertEqual(test_commands(self.project), [])
        root_files.assert_not_called()


if __name__ == '__main__':
    unittest.main()
