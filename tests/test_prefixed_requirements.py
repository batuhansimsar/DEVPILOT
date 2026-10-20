"""Prefixed requirements files must be discovered consistently across commands."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import detect_projects
from devpilot.deps import scan
from devpilot.requirements_names import is_requirements_manifest
from devpilot.workspaces import discover_workspaces


class PrefixedRequirementsTests(unittest.TestCase):
    def test_names_supported_without_accepting_unrelated_files(self):
        for filename in (
            'requirements.txt', 'requirements.in', 'requirements-dev.txt',
            'dev-requirements.txt', 'test-requirements.in',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_requirements_manifest(filename))
        for filename in (
            'dev-requirements.md', 'requirements.md',
            'notrequirements.md', 'myrequirements.txt',
            'dev-requirements.txt.bak',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_requirements_manifest(filename))

    def test_prefixed_file_is_visible_in_deps_doctor_detection_and_workspaces(self):
        for filename in ('dev-requirements.txt', 'test-requirements.in'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / filename).write_text('Requests>=2\n', encoding='utf-8')
                inventory = scan(root)
                self.assertEqual(inventory['warnings'], [])
                self.assertEqual(inventory['manifests'][0]['path'], filename)
                self.assertEqual(inventory['manifests'][0]['groups']['requirements'], ['requests'])
                self.assertIn('Python', detect_projects(root))
                workspace = discover_workspaces(root)
                self.assertEqual(workspace['workspace_count'], 1)
                self.assertIn('Python', workspace['workspaces'][0]['ecosystems'])


if __name__ == '__main__':
    unittest.main()
