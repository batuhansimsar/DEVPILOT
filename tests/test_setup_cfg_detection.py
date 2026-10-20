"""Root-level Setuptools configuration must match workspace project detection."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import detect_projects
from devpilot.workspaces import discover_workspaces


class SetupCfgDetectionTests(unittest.TestCase):
    def test_setup_cfg_only_root_is_python_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'setup.cfg').write_text('[metadata]\nname = example\n')
            self.assertIn('Python', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Python'])

    def test_setup_cfg_backup_does_not_mark_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'setup.cfg.bak').write_text('[metadata]\nname = example\n')
            self.assertNotIn('Python', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)

    def test_symlinked_setup_cfg_is_not_project_marker(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'setup.cfg'
            target.write_text('[metadata]\nname = private\n')
            try:
                (root / 'setup.cfg').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Python', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
