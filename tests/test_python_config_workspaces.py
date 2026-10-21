"""Recognize Python test configuration as project metadata, even without a build manifest."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, test_commands
from devpilot.workspaces import discover_workspaces


class PythonConfigWorkspaceTests(unittest.TestCase):
    def test_config_only_root_is_detected_and_can_offer_tests(self):
        for filename in ('pytest.ini', 'tox.ini'):
            with self.subTest(filename=filename), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).write_text('[pytest]\n', encoding='utf-8')
                (root / 'tests').mkdir()

                self.assertIn('Python', detect_projects(root))
                report = analyze_project(root)
                self.assertIn('Python', report['project_types'])
                self.assertIn(filename, report['key_files'])

                workspaces = discover_workspaces(root)
                self.assertEqual(workspaces['workspace_count'], 1)
                self.assertEqual(workspaces['workspaces'][0]['manifests'], [
                    {'file': filename, 'ecosystem': 'Python'},
                ])

                with patch('devpilot.core.shutil.which', return_value='/usr/bin/pytest'):
                    commands = test_commands(root)
                self.assertTrue(any(cmd['ecosystem'] == 'Python'
                                    and cmd['argv'][-2:] == ['-m', 'pytest']
                                    for cmd in commands))

    def test_nested_config_only_workspace_is_detected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'packages' / 'service'
            nested.mkdir(parents=True)
            (nested / 'tox.ini').write_text('[tox]\n', encoding='utf-8')

            result = discover_workspaces(root)
            self.assertEqual(result['workspace_count'], 1)
            self.assertEqual(result['workspaces'][0]['path'], 'packages/service')
            self.assertEqual(result['workspaces'][0]['ecosystems'], ['Python'])

    def test_symlinked_config_does_not_create_python_project(self):
        with TemporaryDirectory() as directory, TemporaryDirectory() as other:
            root = Path(directory)
            external = Path(other) / 'pytest.ini'
            external.write_text('[pytest]\n', encoding='utf-8')
            try:
                (root / 'pytest.ini').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('Symbolic links unavailable')
            self.assertNotIn('Python', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
