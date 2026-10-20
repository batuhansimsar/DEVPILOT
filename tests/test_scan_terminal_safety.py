"""Regression checks for safe terminal rendering of untrusted scan metadata."""

import unittest

from devpilot.cli import _human


class ScanTerminalSafetyTests(unittest.TestCase):
    def setUp(self):
        self.hostile = 'unsafe\x1b[31m\n\u202e'
        self.escaped = r'unsafe\x1b[31m\x0a\u202e'

    def assert_safe(self, result):
        self.assertIn(self.escaped, result)
        self.assertNotIn('\x1b', result)
        self.assertNotIn('\u202e', result)

    def test_workspace_names_and_scan_failures_are_escaped(self):
        report = {
            'path': self.hostile, 'workspace_count': 1, 'truncated': True,
            'workspaces': [{'path': self.hostile, 'ecosystems': ['Python']}],
            'problems': ['Cannot inspect ' + self.hostile],
        }
        self.assert_safe(_human('workspaces', report))

    def test_analyze_manifest_scripts_and_scan_failures_are_escaped(self):
        report = {
            'path': self.hostile, 'project_types': ['Node.js'],
            'file_count': 1, 'truncated': False, 'languages': {},
            'key_files': [self.hostile], 'npm_scripts': [self.hostile],
            'problems': ['Cannot inspect ' + self.hostile],
        }
        self.assert_safe(_human('analyze', report))

    def test_dependencies_manifest_names_and_warnings_are_escaped(self):
        report = {
            'root': self.hostile,
            'manifests': [{
                'ecosystem': 'Node.js', 'path': self.hostile,
                'count': 1, 'groups': {'dependencies': [self.hostile]},
            }],
            'warnings': ['Cannot inspect ' + self.hostile],
        }
        self.assert_safe(_human('deps', report))


if __name__ == '__main__':
    unittest.main()
