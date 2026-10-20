"""Pipenv lockfiles are project markers, even without a Pipfile."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import KEY_FILES, analyze_project, detect_projects, test_commands
from devpilot.workspaces import discover_workspaces


class PipenvWorkspaceDetectionTests(unittest.TestCase):
    def test_lockfile_only_project_is_detected_at_root_and_nested(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Pipfile.lock').write_text('{}', encoding='utf-8')
            nested = root / 'services' / 'api'
            nested.mkdir(parents=True)
            (nested / 'Pipfile.lock').write_text('{}', encoding='utf-8')

            self.assertIn('Python', detect_projects(root))
            report = discover_workspaces(root)
            self.assertFalse(report['truncated'])
            self.assertEqual(
                [(item['path'], item['manifests']) for item in report['workspaces']],
                [('.', [{'file': 'Pipfile.lock', 'ecosystem': 'Python'}]),
                 ('services/api', [{'file': 'Pipfile.lock', 'ecosystem': 'Python'}])],
            )

    def test_lockfile_and_pipfile_are_grouped_in_one_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Pipfile').write_text('[packages]\n', encoding='utf-8')
            (root / 'Pipfile.lock').write_text('{}', encoding='utf-8')
            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 1)
            self.assertEqual(result['workspaces'][0]['ecosystems'], ['Python'])
            self.assertEqual([x['file'] for x in result['workspaces'][0]['manifests']],
                             ['Pipfile', 'Pipfile.lock'])

    def test_analyze_and_test_plan_recognize_lockfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Pipfile.lock').write_text('{}', encoding='utf-8')
            (root / 'tests').mkdir()
            self.assertIn('Pipfile.lock', KEY_FILES)
            report = analyze_project(root)
            self.assertEqual(report['project_types'], ['Python'])
            self.assertIn('Pipfile.lock', report['key_files'])
            self.assertTrue(any(command['ecosystem'] == 'Python'
                                for command in test_commands(root)))

    def test_symlinked_lockfile_cannot_fake_project(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'Pipfile.lock'
            target.write_text('{}', encoding='utf-8')
            try:
                (root / 'Pipfile.lock').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks are unavailable')
            self.assertNotIn('Python', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
