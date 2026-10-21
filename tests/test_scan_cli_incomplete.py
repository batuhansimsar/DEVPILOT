"""CLI regression: bounded scans with omitted entries must exit nonzero."""

import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from devpilot.cli import main


class ScanCliIncompleteTests(unittest.TestCase):
    def invoke(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(argv)
        return status, json.loads(output.getvalue())

    def test_analyze_truncation_without_problems_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            report = {
                'path': directory, 'project_types': [], 'file_count': 0,
                'truncated': True, 'languages': {}, 'key_files': [],
                'npm_scripts': [], 'problems': [],
            }
            with patch('devpilot.cli.analyze_project', return_value=report):
                status, output = self.invoke(['analyze', '--path', directory, '--json'])
        self.assertEqual(status, 1)
        self.assertTrue(output['truncated'])

    def test_workspaces_truncation_without_problems_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            report = {
                'path': directory, 'workspaces': [], 'workspace_count': 0,
                'truncated': True, 'problems': [],
            }
            with patch('devpilot.cli.discover_workspaces', return_value=report):
                status, output = self.invoke(['workspaces', '--path', directory, '--json'])
        self.assertEqual(status, 1)
        self.assertTrue(output['truncated'])


if __name__ == '__main__':
    unittest.main()
